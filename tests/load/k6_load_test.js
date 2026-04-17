/**
 * k6 Load Test - Kuwait WhatsApp Growth Engine
 *
 * Run: k6 run tests/load/k6_load_test.js
 * With env: k6 run -e BASE_URL=https://app.kwgrowth.com tests/load/k6_load_test.js
 */

import http from "k6/http";
import { check, sleep, group } from "k6";
import { Rate, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const TEST_EMAIL = __ENV.TEST_EMAIL || "loadtest@test.kw";
const TEST_PASSWORD = __ENV.TEST_PASSWORD || "Test1234!";

const errorRate = new Rate("errors");
const apiDuration = new Trend("api_duration", true);

export const options = {
  stages: [
    { duration: "30s", target: 10 },   // Ramp up
    { duration: "1m", target: 50 },    // Sustain 50 users
    { duration: "2m", target: 100 },   // Peak 100 users
    { duration: "1m", target: 50 },    // Cool down
    { duration: "30s", target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ["p(95)<500", "p(99)<1000"],
    errors: ["rate<0.05"],
  },
};

export function setup() {
  // Register test user
  http.post(`${BASE_URL}/v1/auth/register`, JSON.stringify({
    email: TEST_EMAIL,
    username: "loadtest",
    password: TEST_PASSWORD,
    company_name: "Load Test Co",
    first_name: "Load",
    last_name: "Tester",
  }), { headers: { "Content-Type": "application/json" } });

  // Login
  const loginRes = http.post(`${BASE_URL}/v1/auth/login`, JSON.stringify({
    email: TEST_EMAIL,
    password: TEST_PASSWORD,
  }), { headers: { "Content-Type": "application/json" } });

  const token = JSON.parse(loginRes.body).access_token;
  return { token };
}

export default function (data) {
  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${data.token}`,
  };

  group("Health Check", () => {
    const res = http.get(`${BASE_URL}/health/ready`);
    check(res, { "health 200": (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
  });

  group("List Contacts", () => {
    const res = http.get(`${BASE_URL}/v1/contacts?limit=20`, { headers });
    check(res, { "contacts 200": (r) => r.status === 200 });
    apiDuration.add(res.timings.duration);
    errorRate.add(res.status !== 200);
  });

  group("List Conversations", () => {
    const res = http.get(`${BASE_URL}/v1/conversations?limit=20`, { headers });
    check(res, { "conversations 200": (r) => r.status === 200 });
    apiDuration.add(res.timings.duration);
    errorRate.add(res.status !== 200);
  });

  group("Analytics Dashboard", () => {
    const res = http.get(`${BASE_URL}/v1/analytics/dashboard?days=30`, { headers });
    check(res, { "analytics 200": (r) => r.status === 200 });
    apiDuration.add(res.timings.duration);
    errorRate.add(res.status !== 200);
  });

  group("List Tags", () => {
    const res = http.get(`${BASE_URL}/v1/tags`, { headers });
    check(res, { "tags 200": (r) => r.status === 200 });
    apiDuration.add(res.timings.duration);
    errorRate.add(res.status !== 200);
  });

  sleep(1);
}
