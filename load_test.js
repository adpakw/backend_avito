import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Кастомные метрики
export const errorRate = new Rate('errors');
export const predictionDuration = new Trend('prediction_duration');
export const cacheHitRate = new Rate('cache_hits');
export const asyncTasksCreated = new Counter('async_tasks_created');

export const options = {
  // Разные сценарии нагрузки
  scenarios: {
    // Постепенное увеличение нагрузки
    ramp_up: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 10 },   // разогрев
        { duration: '3m', target: 50 },    // пиковая нагрузка
        { duration: '1m', target: 100 },    // максимальная нагрузка
        { duration: '1m', target: 0 },      // спад
      ],
      gracefulRampDown: '30s',
    },
    // Постоянная нагрузка
    constant_load: {
      executor: 'constant-vus',
      vus: 30,
      duration: '5m',
      startTime: '5m',  // начинается после ramp_up
    },
    // Внезапные всплески
    spikes: {
      executor: 'ramping-arrival-rate',
      startRate: 50,
      timeUnit: '1s',
      preAllocatedVUs: 50,
      maxVUs: 100,
      stages: [
        { duration: '10s', target: 200 },   // резкий всплеск
        { duration: '30s', target: 200 },    // удержание
        { duration: '10s', target: 50 },     // спад
      ],
      startTime: '11m',
    },
  },
  
  // Пороговые значения для проверок
  thresholds: {
    http_req_duration: ['p(95)<1000', 'p(99)<2000'], // 95% запросов < 1s, 99% < 2s
    http_req_failed: ['rate<0.05'],                   // менее 5% ошибок
    errors: ['rate<0.1'],                              // менее 10% кастомных ошибок
    cache_hits: ['rate>0.3'],                          // более 30% попаданий в кэш
    'prediction_duration': ['p(95)<500'],              // 95% предсказаний < 500ms
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Тестовые данные
const testAds = [
  { seller_id: 1, is_verified_seller: true, item_id: 1, name: "Ноутбук", description: "Игровой ноутбук", category: 5, images_qty: 3 },
  { seller_id: 2, is_verified_seller: false, item_id: 2, name: "Телефон", description: "Смартфон", category: 3, images_qty: 2 },
  { seller_id: 3, is_verified_seller: true, item_id: 3, name: "Книга", description: "Учебник по Python", category: 2, images_qty: 1 },
  { seller_id: 1, is_verified_seller: true, item_id: 4, name: "Велосипед", description: "Горный велосипед", category: 7, images_qty: 4 },
  { seller_id: 2, is_verified_seller: false, item_id: 5, name: "Диван", description: "Мягкий диван", category: 8, images_qty: 3 },
];

// Валидные ID для simple_predict
const validItemIds = [1, 2, 3, 4, 5];

// Хранилище созданных task_id для проверки результатов
const taskIds = [];

export default function() {
  // Группируем запросы по типам для лучшей читаемости в отчетах
  group('Sync Predictions', function() {
    testSyncPredictions();
  });
  
  group('Cached Predictions', function() {
    testCachedPredictions();
  });
  
  group('Async Predictions', function() {
    testAsyncPredictions();
  });
  
  group('Health Check', function() {
    testHealthEndpoint();
  });
  
  // Периодически проверяем результаты асинхронных задач
  if (__ITER % 10 === 0 && taskIds.length > 0) {
    group('Check Moderation Results', function() {
      checkModerationResults();
    });
  }
  
  sleep(0.5); // Пауза между итерациями
}

function testSyncPredictions() {
  // Выбираем случайное объявление из тестовых данных
  const ad = testAds[Math.floor(Math.random() * testAds.length)];
  
  const startTime = Date.now();
  
  const response = http.post(
    `${BASE_URL}/predict`,
    JSON.stringify(ad),
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { endpoint: 'predict', type: 'sync' },
    }
  );
  
  const duration = Date.now() - startTime;
  predictionDuration.add(duration);
  
  // Проверки
  const success = check(response, {
    'sync predict status is 200': (r) => r.status === 200,
    'sync predict has is_violation field': (r) => JSON.parse(r.body).hasOwnProperty('is_violation'),
    'sync predict has probability field': (r) => JSON.parse(r.body).hasOwnProperty('probability'),
    'sync predict probability in range': (r) => {
      const prob = JSON.parse(r.body).probability;
      return prob >= 0 && prob <= 1;
    },
  });
  
  if (!success) {
    errorRate.add(1);
    console.log(`Sync predict failed: ${response.status} - ${response.body}`);
  }
}

function testCachedPredictions() {
  // simple_predict должен использовать кэш
  const itemId = validItemIds[Math.floor(Math.random() * validItemIds.length)];
  
  const startTime = Date.now();
  
  const response = http.post(
    `${BASE_URL}/simple_predict`,
    JSON.stringify({ id: itemId }),
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { endpoint: 'simple_predict', type: 'cached' },
    }
  );
  
  const duration = Date.now() - startTime;
  
  // Для cached predictions проверяем, что время ответа малое
  if (duration < 100) {
    cacheHitRate.add(1);
  } else {
    cacheHitRate.add(0);
  }
  
  const success = check(response, {
    'simple predict status is 200': (r) => r.status === 200,
    'simple predict returns valid result': (r) => {
      const body = JSON.parse(r.body);
      return body.hasOwnProperty('is_violation') && body.hasOwnProperty('probability');
    },
  });
  
  if (!success) {
    errorRate.add(1);
  }
}

function testAsyncPredictions() {
  const itemId = validItemIds[Math.floor(Math.random() * validItemIds.length)];
  
  const response = http.post(
    `${BASE_URL}/async_predict`,
    JSON.stringify({ id: itemId }),
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { endpoint: 'async_predict', type: 'async' },
    }
  );
  
  const success = check(response, {
    'async predict status is 200': (r) => r.status === 200,
    'async predict returns task_id': (r) => {
      const body = JSON.parse(r.body);
      return body.hasOwnProperty('task_id') && body.task_id > 0;
    },
    'async predict status is pending': (r) => {
      const body = JSON.parse(r.body);
      return body.status === 'pending';
    },
  });
  
  if (success) {
    const taskId = JSON.parse(response.body).task_id;
    taskIds.push(taskId);
    asyncTasksCreated.add(1);
  } else {
    errorRate.add(1);
  }
}

function testHealthEndpoint() {
  const response = http.get(`${BASE_URL}/health`);
  
  check(response, {
    'health status is 200': (r) => r.status === 200,
    'health returns healthy': (r) => JSON.parse(r.body).status === 'healthy',
    'health confirms model loaded': (r) => {
      const body = JSON.parse(r.body);
      return body.model_loaded === true || body.model_loaded === null;
    },
  });
}

function checkModerationResults() {
  // Проверяем до 5 случайных task_id
  const tasksToCheck = Math.min(5, taskIds.length);
  const shuffled = [...taskIds].sort(() => 0.5 - Math.random());
  
  for (let i = 0; i < tasksToCheck; i++) {
    const taskId = shuffled[i];
    
    const response = http.get(
      `${BASE_URL}/moderation_result/${taskId}`,
      { tags: { endpoint: 'moderation_result' } }
    );
    
    const success = check(response, {
      'moderation result returns 200': (r) => r.status === 200,
      'moderation result has valid status': (r) => {
        const body = JSON.parse(r.body);
        return ['pending', 'completed', 'failed'].includes(body.status);
      },
    });
    
    if (!success) {
      errorRate.add(1);
    }
    
    sleep(0.1);
  }
}

// Функция для кастомного завершения
export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'summary.json': JSON.stringify(data, null, 2),
  };
}

// Функция для цветного вывода
function textSummary(data, options) {
  // Стандартная реализация summary
  return `
=== Результаты нагрузочного тестирования ===
Длительность: ${data.state.testRunDurationMs / 1000}с
Всего запросов: ${data.metrics.http_reqs.values.count}
Среднее время ответа: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms
p95 время ответа: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms
p99 время ответа: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms
Процент ошибок: ${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%
Скорость запросов: ${data.metrics.http_reqs.values.rate.toFixed(2)} rps

=== Кастомные метрики ===
Ошибки приложений: ${(data.metrics.errors.values.rate * 100).toFixed(2)}%
Попадания в кэш: ${(data.metrics.cache_hits.values.rate * 100).toFixed(2)}%
Среднее время предсказания: ${data.metrics.prediction_duration.values.avg.toFixed(2)}ms
p95 время предсказания: ${data.metrics.prediction_duration.values['p(95)'].toFixed(2)}ms
Создано асинхронных задач: ${data.metrics.async_tasks_created.values.count}
`;
}