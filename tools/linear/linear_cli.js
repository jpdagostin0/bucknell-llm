#!/usr/bin/env node
"use strict";

const fs = require("fs");
const http = require("http");
const https = require("https");
const path = require("path");
const { LinearClient } = require("@linear/sdk");
const { parse: parseYaml } = require("yaml");

function vaultRoot() {
  return path.resolve(__dirname, "..", "..");
}

function loadEnv() {
  const envFile = path.join(vaultRoot(), ".env.yml");
  if (!fs.existsSync(envFile)) {
    throw Object.assign(new Error("Missing .env.yml at the vault root."), {
      code: "missing_secrets",
    });
  }
  const loaded = parseYaml(fs.readFileSync(envFile, "utf8")) || {};
  return loaded;
}

function linearApiKey() {
  const key = String((loadEnv().linear || {}).api_key || "").trim();
  if (!key) {
    throw Object.assign(new Error("Set linear.api_key in .env.yml."), {
      code: "missing_secrets",
    });
  }
  return key;
}

function toSnake(name) {
  return String(name)
    .replace(/-/g, "_")
    .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
    .toLowerCase();
}

function toCamel(name) {
  const parts = toSnake(name).split("_");
  return parts[0] + parts.slice(1).map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join("");
}

function keyVariants(name) {
  const snake = toSnake(name);
  const camel = toCamel(name);
  const kebab = snake.replace(/_/g, "-");
  return [...new Set([name, snake, camel, kebab])];
}

function getValue(payload, names, options = {}) {
  const { required = false, defaultValue = undefined } = options;
  for (const name of names) {
    for (const candidate of keyVariants(name)) {
      if (payload[candidate] !== undefined && payload[candidate] !== null) {
        return payload[candidate];
      }
    }
  }
  if (required) {
    throw Object.assign(new Error(`Missing required argument: ${names[0]}`), {
      code: "usage",
    });
  }
  return defaultValue;
}

function isSandboxOrScratchpadPath(raw) {
  const text = String(raw).replace(/\\/g, "/").toLowerCase();
  if (text.includes(".lmstudio/scratchpads")) return true;
  if (text === "/inputs" || text.startsWith("/inputs/")) return true;
  if (text === "/outputs" || text.startsWith("/outputs/")) return true;
  return false;
}

function parseFlagValue(raw) {
  const text = String(raw).trim();
  const lowered = text.toLowerCase();
  if (["true", "yes"].includes(lowered)) return true;
  if (["false", "no"].includes(lowered)) return false;
  if (["null", "none"].includes(lowered)) return null;
  if (/^-?\d+$/.test(text)) return Number(text);
  if (text.startsWith("{") || text.startsWith("[")) {
    try {
      return JSON.parse(text);
    } catch {
      return text;
    }
  }
  return text;
}

function assignFlag(payload, seen, key, value) {
  if (seen.has(key)) {
    const existing = payload[key];
    const extra = Array.isArray(value) ? value : [value];
    if (Array.isArray(existing)) {
      existing.push(...extra);
    } else {
      payload[key] = [existing, ...extra];
    }
    return;
  }
  seen.add(key);
  payload[key] = value;
}

function loadJsonObject(raw, source) {
  let loaded;
  try {
    loaded = JSON.parse(raw);
  } catch (error) {
    throw Object.assign(new Error(`${source} is not valid JSON: ${error.message}`), {
      code: "usage",
    });
  }
  if (!loaded || typeof loaded !== "object" || Array.isArray(loaded)) {
    throw Object.assign(new Error(`${source} must contain a JSON object`), {
      code: "usage",
    });
  }
  return loaded;
}

function loadJsonFile(raw) {
  if (isSandboxOrScratchpadPath(raw)) {
    throw Object.assign(
      new Error(
        `--json-file ${raw} is not on the host filesystem. Use payload.json or pass --flag values.`
      ),
      { code: "usage" }
    );
  }
  if (!fs.existsSync(raw)) {
    throw Object.assign(
      new Error(
        `--json-file not found: ${raw}. Use a vault-relative host path such as payload.json, or pass --flag values instead.`
      ),
      { code: "usage" }
    );
  }
  return loadJsonObject(fs.readFileSync(raw, "utf8"), "--json-file");
}

function normalizeLabelIds(value) {
  if (value == null || value === "") return undefined;
  if (Array.isArray(value)) {
    return value.map((item) => String(item)).filter(Boolean);
  }
  const text = String(value).trim();
  if (text.startsWith("[")) {
    try {
      const parsed = JSON.parse(text);
      if (Array.isArray(parsed)) return parsed.map((item) => String(item)).filter(Boolean);
    } catch {
      // Unquoted [uuid] arrays may arrive without JSON quotes.
    }
    return text
      .replace(/^\[/, "")
      .replace(/\]$/, "")
      .split(",")
      .map((part) => part.trim().replace(/^["']|["']$/g, ""))
      .filter(Boolean);
  }
  return text.split(",").map((part) => part.trim()).filter(Boolean);
}

function parseInvocation(argv) {
  const args = argv.slice(2);
  if (
    args.length === 0 ||
    args.includes("--help") ||
    args.includes("-h") ||
    ["help", "commands", "--list"].includes(args[0])
  ) {
    return { command: "commands", payload: {} };
  }
  const command = args[0].startsWith("-") ? "commands" : args[0];
  const start = args[0].startsWith("-") ? 0 : 1;
  const payload = {};
  const seen = new Set();
  let jsonText = null;
  let jsonFile = null;
  let key = null;
  for (let index = start; index < args.length; index += 1) {
    const token = args[index];
    if (token === "--json" || token === "--json-file") {
      const value = args[index + 1];
      if (value == null) {
        throw Object.assign(new Error(`${token} requires a value`), { code: "usage" });
      }
      if (token === "--json") jsonText = value;
      else jsonFile = value;
      index += 1;
      key = null;
      continue;
    }
    if (token.startsWith("--json=") || token.startsWith("--json-file=")) {
      const eq = token.indexOf("=");
      const name = token.slice(2, eq);
      const value = token.slice(eq + 1);
      if (name === "json") jsonText = value;
      else jsonFile = value;
      key = null;
      continue;
    }
    if (token.startsWith("--") && token.includes("=")) {
      const [name, value] = token.slice(2).split("=");
      assignFlag(payload, seen, name, parseFlagValue(value));
      key = null;
      continue;
    }
    if (token.startsWith("--")) {
      if (key) assignFlag(payload, seen, key, true);
      key = token.slice(2);
      continue;
    }
    if (!key) {
      throw Object.assign(new Error(`Unexpected argument: ${token}`), {
        code: "usage",
      });
    }
    assignFlag(payload, seen, key, parseFlagValue(token));
    key = null;
  }
  if (key) assignFlag(payload, seen, key, true);
  const merged = {};
  if (jsonFile) Object.assign(merged, loadJsonFile(jsonFile));
  if (jsonText) Object.assign(merged, loadJsonObject(jsonText, "--json"));
  Object.assign(merged, payload);
  return { command, payload: merged };
}

function emit(payload, error = false) {
  const stream = error ? process.stderr : process.stdout;
  stream.write(`${JSON.stringify(payload, null, 2)}\n`);
}

function client() {
  return new LinearClient({ apiKey: linearApiKey() });
}

async function related(entity, field) {
  if (!entity || typeof entity[field] !== "function") {
    return entity?.[field] ?? null;
  }
  try {
    return await entity[field]();
  } catch {
    return null;
  }
}

function pageInfo(connection) {
  return {
    hasNextPage: Boolean(connection?.pageInfo?.hasNextPage),
    endCursor: connection?.pageInfo?.endCursor ?? null,
  };
}

function serializeCycle(cycle) {
  if (!cycle) return null;
  return {
    id: cycle.id,
    name: cycle.name ?? null,
    number: cycle.number ?? null,
    startsAt: cycle.startsAt ?? null,
    endsAt: cycle.endsAt ?? null,
    isActive: Boolean(cycle.isActive),
    isNext: Boolean(cycle.isNext),
    isPrevious: Boolean(cycle.isPrevious),
  };
}

function pad2(value) {
  return String(value).padStart(2, "0");
}

function localClock(at = new Date()) {
  const offsetMin = -at.getTimezoneOffset();
  const sign = offsetMin >= 0 ? "+" : "-";
  const abs = Math.abs(offsetMin);
  const offset = `${sign}${pad2(Math.floor(abs / 60))}:${pad2(abs % 60)}`;
  const date = `${at.getFullYear()}-${pad2(at.getMonth() + 1)}-${pad2(at.getDate())}`;
  const time = `${pad2(at.getHours())}:${pad2(at.getMinutes())}:${pad2(at.getSeconds())}`;
  return {
    utc: at.toISOString(),
    local: `${date}T${time}${offset}`,
    date,
    time,
    weekday: at.toLocaleDateString("en-US", { weekday: "long" }),
    timezoneOffset: offset,
  };
}

async function serializeIssue(issue, fields) {
  if (!issue) return null;
  const state = await related(issue, "state");
  const team = await related(issue, "team");
  const project = await related(issue, "project");
  const assignee = await related(issue, "assignee");
  const cycle = await related(issue, "cycle");
  const labelsConn = await related(issue, "labels");
  const payload = {
    id: issue.id,
    identifier: issue.identifier,
    title: issue.title,
    description: issue.description,
    url: issue.url,
    priority: issue.priority,
    estimate: issue.estimate,
    dueDate: issue.dueDate,
    createdAt: issue.createdAt,
    updatedAt: issue.updatedAt,
    status: state?.name ?? null,
    statusType: state?.type ?? null,
    team: team ? { id: team.id, key: team.key, name: team.name } : null,
    project: project ? { id: project.id, name: project.name } : null,
    assignee: assignee
      ? { id: assignee.id, name: assignee.name, email: assignee.email }
      : null,
    cycle: serializeCycle(cycle),
    labels: (labelsConn?.nodes || []).map((label) => ({
      id: label.id,
      name: label.name,
    })),
  };
  if (Array.isArray(fields) && fields.length) {
    const picked = { id: payload.id };
    for (const field of fields) {
      picked[field] = payload[field];
    }
    return picked;
  }
  return payload;
}

async function serializeProject(project) {
  if (!project) return null;
  return {
    id: project.id,
    name: project.name,
    slugId: project.slugId,
    description: project.description,
    url: project.url,
    startDate: project.startDate,
    targetDate: project.targetDate,
    state: project.state,
  };
}

async function ping() {
  const linear = client();
  const viewer = await linear.viewer;
  const workspace = await linear.organization;
  return {
    service: "linear",
    viewer: { id: viewer.id, name: viewer.name, email: viewer.email },
    workspace: { id: workspace.id, name: workspace.name, urlKey: workspace.urlKey },
  };
}

async function getWorkspace() {
  const workspace = await client().organization;
  return {
    id: workspace.id,
    name: workspace.name,
    urlKey: workspace.urlKey,
  };
}

async function listTeams(payload) {
  const connection = await client().teams({
    first: Number(getValue(payload, ["limit", "first"], { defaultValue: 50 })),
    after: getValue(payload, ["cursor", "after"]),
  });
  return {
    teams: connection.nodes.map((team) => ({
      id: team.id,
      key: team.key,
      name: team.name,
    })),
    pageInfo: pageInfo(connection),
  };
}

async function getTeam(payload) {
  const id = getValue(payload, ["id", "team"], { required: true });
  const team = await client().team(id);
  return { id: team.id, key: team.key, name: team.name };
}

async function listUsers(payload) {
  const connection = await client().users({
    first: Number(getValue(payload, ["limit", "first"], { defaultValue: 50 })),
    after: getValue(payload, ["cursor", "after"]),
  });
  return {
    users: connection.nodes.map((user) => ({
      id: user.id,
      name: user.name,
      email: user.email,
      displayName: user.displayName,
    })),
    pageInfo: pageInfo(connection),
  };
}

async function getUser(payload) {
  const id = getValue(payload, ["id"], { required: true });
  if (id === "me") {
    const viewer = await client().viewer;
    return { id: viewer.id, name: viewer.name, email: viewer.email };
  }
  const user = await client().user(id);
  return { id: user.id, name: user.name, email: user.email };
}

async function listProjects(payload) {
  const filter = {};
  const query = getValue(payload, ["query"]);
  const team = getValue(payload, ["team"]);
  if (query) filter.name = { containsIgnoreCase: query };
  if (team) filter.accessibleTeams = { or: [{ id: { eq: team } }, { key: { eq: team } }, { name: { eq: team } }] };
  const connection = await client().projects({
    first: Number(getValue(payload, ["limit", "first"], { defaultValue: 50 })),
    after: getValue(payload, ["cursor", "after"]),
    filter: Object.keys(filter).length ? filter : undefined,
  });
  return {
    projects: await Promise.all(connection.nodes.map(serializeProject)),
    pageInfo: pageInfo(connection),
  };
}

async function getProject(payload) {
  const id = getValue(payload, ["id", "project"], { required: true });
  return serializeProject(await client().project(id));
}

async function saveProject(payload) {
  const linear = client();
  const id = getValue(payload, ["id"]);
  const input = {
    name: getValue(payload, ["name"]),
    description: getValue(payload, ["description"]),
    startDate: getValue(payload, ["startDate", "start_date"]),
    targetDate: getValue(payload, ["targetDate", "target_date"]),
  };
  Object.keys(input).forEach((key) => input[key] === undefined && delete input[key]);
  if (id) {
    const result = await linear.updateProject(id, input);
    return serializeProject(await result.project);
  }
  if (!input.name) {
    throw Object.assign(new Error("name is required when creating a project"), {
      code: "usage",
    });
  }
  const team = getValue(payload, ["team", "teamId", "team_id"]);
  if (team) input.teamIds = [team];
  const result = await linear.createProject(input);
  return serializeProject(await result.project);
}

async function listIssueStatuses(payload) {
  const teamId = getValue(payload, ["team", "teamId", "id"], { required: true });
  const team = await client().team(teamId);
  const states = await team.states();
  return {
    statuses: states.nodes.map((state) => ({
      id: state.id,
      name: state.name,
      type: state.type,
    })),
  };
}

async function getIssueStatus(payload) {
  const id = getValue(payload, ["id"], { required: true });
  const state = await client().workflowState(id);
  return { id: state.id, name: state.name, type: state.type };
}

async function listIssueLabels(payload) {
  const filter = {};
  const team = getValue(payload, ["team"]);
  if (team) filter.team = { or: [{ id: { eq: team } }, { key: { eq: team } }] };
  const connection = await client().issueLabels({
    first: Number(getValue(payload, ["limit", "first"], { defaultValue: 100 })),
    filter: Object.keys(filter).length ? filter : undefined,
  });
  return {
    labels: connection.nodes.map((label) => ({
      id: label.id,
      name: label.name,
    })),
  };
}

async function createIssueLabel(payload) {
  const name = getValue(payload, ["name"], { required: true });
  const teamId = getValue(payload, ["team", "teamId", "team_id"]);
  const result = await client().createIssueLabel({ name, teamId });
  const label = await result.issueLabel;
  return { id: label.id, name: label.name };
}

async function defaultTeam(payload) {
  const value = getValue(payload, ["team", "teamId"]);
  if (value) {
    const id = await resolveTeamId(value);
    const team = await client().team(id);
    return { id: team.id, key: team.key, name: team.name };
  }
  const connection = await client().teams({ first: 50 });
  const match =
    connection.nodes.find((team) => /fall 2026/i.test(String(team.name || ""))) ||
    connection.nodes[0];
  return match ? { id: match.id, key: match.key, name: match.name } : null;
}

async function listCycles(payload) {
  const teamId = getValue(payload, ["team", "teamId", "id"]);
  const teamRef = teamId ? { id: await resolveTeamId(teamId) } : await defaultTeam(payload);
  if (!teamRef) {
    throw Object.assign(new Error("team is required"), { code: "usage" });
  }
  const team = await client().team(teamRef.id);
  const type = String(getValue(payload, ["type"], { defaultValue: "all" }) || "all");
  const relative = cycleRelativeFilter(type);
  if (relative && relative.isActive) {
    const active = await related(team, "activeCycle");
    return { cycles: active ? [serializeCycle(active)] : [] };
  }
  const cycles = await team.cycles({
    first: Number(getValue(payload, ["limit", "first"], { defaultValue: 50 })),
    filter: relative || undefined,
  });
  return {
    cycles: cycles.nodes.map(serializeCycle),
  };
}

async function listMilestones(payload) {
  const projectId = getValue(payload, ["project", "projectId", "id"]);
  const connection = await client().projectMilestones({
    first: Number(getValue(payload, ["limit", "first"], { defaultValue: 50 })),
    filter: projectId ? { project: { id: { eq: projectId } } } : undefined,
  });
  return {
    milestones: connection.nodes.map((item) => ({
      id: item.id,
      name: item.name,
      targetDate: item.targetDate,
    })),
  };
}

async function getMilestone(payload) {
  const id = getValue(payload, ["id"], { required: true });
  const milestone = await client().projectMilestone(id);
  return { id: milestone.id, name: milestone.name, targetDate: milestone.targetDate };
}

async function saveMilestone(payload) {
  const linear = client();
  const id = getValue(payload, ["id"]);
  const input = {
    name: getValue(payload, ["name"]),
    targetDate: getValue(payload, ["targetDate", "target_date"]),
    projectId: getValue(payload, ["project", "projectId", "project_id"]),
  };
  Object.keys(input).forEach((key) => input[key] === undefined && delete input[key]);
  if (id) {
    const result = await linear.updateProjectMilestone(id, input);
    const milestone = await result.projectMilestone;
    return { id: milestone.id, name: milestone.name, targetDate: milestone.targetDate };
  }
  const result = await linear.createProjectMilestone(input);
  const milestone = await result.projectMilestone;
  return { id: milestone.id, name: milestone.name, targetDate: milestone.targetDate };
}

function isUuid(value) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
    String(value || "")
  );
}

function projectFilterValue(project) {
  const text = String(project);
  if (isUuid(text)) {
    return { id: { eq: text } };
  }
  const suffix = text.match(/([0-9a-f]{8,14})$/i);
  const clauses = [{ name: { eq: text } }];
  if (suffix) {
    clauses.push({ slugId: { eq: suffix[1] } });
  } else if (!text.includes(" ")) {
    clauses.push({ slugId: { eq: text } });
  }
  return clauses.length === 1 ? clauses[0] : { or: clauses };
}

function cycleRelativeFilter(value) {
  if (value === true) return { isActive: { eq: true } };
  const text = String(value || "").trim().toLowerCase();
  if (!text || text === "all") return null;
  if (["current", "active", "now"].includes(text)) return { isActive: { eq: true } };
  if (text === "next") return { isNext: { eq: true } };
  if (["previous", "prev"].includes(text)) return { isPrevious: { eq: true } };
  return null;
}

function cycleNamedFilter(value) {
  const text = String(value).trim();
  if (isUuid(text)) return { id: { eq: text } };
  const match = text.match(/^(?:week\s+)?(\d+)$/i);
  const clauses = [{ name: { eq: text } }];
  if (match) {
    const num = Number(match[1]);
    clauses.push({ number: { eq: num } });
    clauses.push({ name: { eq: `Week ${pad2(num)}` } });
    clauses.push({ name: { eq: `Week ${num}` } });
  }
  const seen = new Set();
  const unique = [];
  for (const clause of clauses) {
    const key = JSON.stringify(clause);
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(clause);
  }
  return unique.length === 1 ? unique[0] : { or: unique };
}

function cycleFilter(cycle) {
  if (cycle == null || cycle === "") return undefined;
  return cycleRelativeFilter(cycle) || cycleNamedFilter(cycle);
}

function issueFilter(payload) {
  const filter = {};
  const query = getValue(payload, ["query"]);
  const team = getValue(payload, ["team"]);
  const state = getValue(payload, ["state"]);
  const project = getValue(payload, ["project"]);
  const label = getValue(payload, ["label"]);
  const cycle = getValue(payload, ["cycle"]);
  const assignee = getValue(payload, ["assignee"]);
  const parentId = getValue(payload, ["parentId", "parent_id"]);
  const priority = getValue(payload, ["priority"]);
  if (query) filter.or = [{ title: { containsIgnoreCase: query } }, { description: { containsIgnoreCase: query } }];
  if (team) filter.team = { or: [{ id: { eq: team } }, { key: { eq: team } }, { name: { eq: team } }] };
  if (state) filter.state = { or: [{ id: { eq: state } }, { name: { eq: state } }, { type: { eq: state } }] };
  if (project) filter.project = projectFilterValue(project);
  if (label) filter.labels = { or: [{ id: { eq: label } }, { name: { eq: label } }] };
  const cycleValue = cycleFilter(cycle);
  if (cycleValue) filter.cycle = cycleValue;
  if (assignee === "me") filter.assignee = { isMe: { eq: true } };
  else if (assignee === null) filter.assignee = { null: true };
  else if (assignee) filter.assignee = { or: [{ id: { eq: assignee } }, { email: { eq: assignee } }, { name: { eq: assignee } }] };
  if (parentId) filter.parent = { or: [{ id: { eq: parentId } }, { identifier: { eq: parentId } }] };
  if (priority !== undefined) filter.priority = { eq: Number(priority) };
  return Object.keys(filter).length ? filter : undefined;
}

async function collectIssues(payload, { all = false } = {}) {
  const fields = getValue(payload, ["fields"]);
  const includeArchived = Boolean(
    getValue(payload, ["includeArchived", "include_archived"], { defaultValue: false })
  );
  const pageSize = Math.min(
    250,
    Math.max(1, Number(getValue(payload, ["limit", "first"], { defaultValue: 50 })))
  );
  let after = getValue(payload, ["cursor", "after"]);
  const issues = [];
  let lastPage = { hasNextPage: false, endCursor: null };
  const maxPages = all ? 20 : 1;
  for (let index = 0; index < maxPages; index += 1) {
    const connection = await client().issues({
      first: pageSize,
      after,
      filter: issueFilter(payload),
      includeArchived,
    });
    issues.push(
      ...(await Promise.all(connection.nodes.map((issue) => serializeIssue(issue, fields))))
    );
    lastPage = pageInfo(connection);
    if (!lastPage.hasNextPage || !lastPage.endCursor) break;
    after = lastPage.endCursor;
  }
  return { issues, pageInfo: lastPage };
}

async function listIssues(payload) {
  return collectIssues(payload, { all: false });
}

async function allIssues(payload) {
  const listed = await collectIssues(payload, { all: true });
  return {
    issues: listed.issues,
    count: listed.issues.length,
    pageInfo: listed.pageInfo,
  };
}

async function currentCycleIssues(payload) {
  const team = await defaultTeam(payload);
  const merged = { ...payload, cycle: "current" };
  if (team && !getValue(payload, ["team", "teamId"])) {
    merged.team = team.id;
  }
  const listed = await collectIssues(merged, { all: true });
  let cycle = null;
  if (team) {
    const current = await listCycles({ team: team.id, type: "current" });
    cycle = current.cycles[0] || null;
  }
  return {
    cycle,
    issues: listed.issues,
    count: listed.issues.length,
    pageInfo: listed.pageInfo,
  };
}

async function now(payload) {
  const clock = localClock();
  const team = await defaultTeam(payload);
  let cycle = null;
  let previousCycle = null;
  let nextCycle = null;
  if (team) {
    const listed = await listCycles({ team: team.id, limit: 50, type: "all" });
    const cycles = listed.cycles || [];
    cycle = cycles.find((item) => item && item.isActive) || null;
    previousCycle = cycles.find((item) => item && item.isPrevious) || null;
    nextCycle = cycles.find((item) => item && item.isNext) || null;
    if (!cycle) {
      const current = await listCycles({ team: team.id, type: "current" });
      cycle = current.cycles[0] || null;
    }
  }
  return {
    ...clock,
    team,
    cycle,
    previousCycle,
    nextCycle,
  };
}

async function getIssue(payload) {
  const id = getValue(payload, ["id"], { required: true });
  const issue = await client().issue(id);
  return serializeIssue(issue);
}

function asArray(value) {
  if (value == null || value === "") return [];
  return Array.isArray(value) ? value : [value];
}

async function resolveTeamId(value) {
  if (!value) return undefined;
  const text = String(value);
  if (isUuid(text)) return text;
  const connection = await client().teams({ first: 50 });
  const match = connection.nodes.find(
    (team) => team.id === text || team.key === text || team.name === text
  );
  if (!match) {
    throw Object.assign(new Error(`Unknown Linear team: ${text}`), { code: "usage" });
  }
  return match.id;
}

async function resolveProjectId(value) {
  if (!value) return undefined;
  const text = String(value);
  if (isUuid(text)) return text;
  const connection = await client().projects({
    first: 50,
    filter: projectFilterValue(text),
  });
  const match =
    connection.nodes.find(
      (project) =>
        project.id === text ||
        project.name === text ||
        project.slugId === text ||
        String(project.url || "") === text
    ) || (connection.nodes.length === 1 ? connection.nodes[0] : null);
  if (!match) {
    throw Object.assign(new Error(`Unknown Linear project: ${text}`), { code: "usage" });
  }
  return match.id;
}

async function resolveCycleId(value) {
  if (value == null || value === "") return undefined;
  const text = String(value);
  if (isUuid(text)) return text;
  const teams = await client().teams({ first: 10 });
  const team = teams.nodes[0];
  if (!team) {
    throw Object.assign(new Error(`Unknown Linear cycle: ${text}`), { code: "usage" });
  }
  const cycles = await team.cycles({ first: 50 });
  const num = Number(text.replace(/^week\s+/i, ""));
  const wanted = new Set(
    [text, `week ${text}`, Number.isFinite(num) ? `week ${String(num).padStart(2, "0")}` : "", Number.isFinite(num) ? `week ${num}` : ""]
      .filter(Boolean)
      .map((item) => item.toLowerCase())
  );
  const match = cycles.nodes.find((cycle) => {
    if (Number.isFinite(num) && cycle.number === num) return true;
    return wanted.has(String(cycle.name || "").toLowerCase());
  });
  if (!match) {
    throw Object.assign(new Error(`Unknown Linear cycle: ${text}`), { code: "usage" });
  }
  return match.id;
}

async function resolveLabelIds(value) {
  const raw = normalizeLabelIds(value);
  if (!raw || !raw.length) return undefined;
  if (raw.every(isUuid)) return raw;
  const connection = await client().issueLabels({ first: 250 });
  const byName = new Map(
    connection.nodes.map((label) => [String(label.name || "").toLowerCase(), label.id])
  );
  return raw.map((item) => {
    if (isUuid(item)) return item;
    const id = byName.get(String(item).toLowerCase());
    if (!id) {
      throw Object.assign(new Error(`Unknown Linear label: ${item}`), { code: "usage" });
    }
    return id;
  });
}

function contentTypeFor(filename) {
  const ext = path.extname(filename).toLowerCase();
  return (
    {
      ".pdf": "application/pdf",
      ".png": "image/png",
      ".jpg": "image/jpeg",
      ".jpeg": "image/jpeg",
      ".gif": "image/gif",
      ".webp": "image/webp",
      ".txt": "text/plain",
      ".md": "text/markdown",
      ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }[ext] || "application/octet-stream"
  );
}

function resolveVaultFile(raw) {
  if (isSandboxOrScratchpadPath(raw)) {
    throw Object.assign(new Error(`File ${raw} is not on the host filesystem.`), {
      code: "usage",
    });
  }
  const candidates = [path.resolve(raw), path.resolve(vaultRoot(), raw)];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) {
      return candidate;
    }
  }
  throw Object.assign(new Error(`Attachment file not found: ${raw}`), { code: "usage" });
}

function putSignedUpload(uploadUrl, headerList, body, contentType) {
  return new Promise((resolve, reject) => {
    const url = new URL(uploadUrl);
    const headers = {};
    for (const header of headerList || []) {
      headers[header.key] = header.value;
    }
    if (!Object.keys(headers).some((key) => key.toLowerCase() === "content-type")) {
      headers["content-type"] = contentType;
    }
    const transport = url.protocol === "http:" ? http : https;
    const req = transport.request(
      {
        protocol: url.protocol,
        hostname: url.hostname,
        port: url.port || undefined,
        path: `${url.pathname}${url.search}`,
        method: "PUT",
        headers,
      },
      (res) => {
        const chunks = [];
        res.on("data", (chunk) => chunks.push(chunk));
        res.on("end", () => {
          const detail = Buffer.concat(chunks).toString("utf8");
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve();
            return;
          }
          reject(
            Object.assign(
              new Error(`Linear file PUT failed (${res.statusCode}): ${detail}`),
              { code: "api" }
            )
          );
        });
      }
    );
    req.on("error", reject);
    req.end(body);
  });
}

async function attachFile(issueId, filePath, title, subtitle) {
  const resolved = resolveVaultFile(filePath);
  const filename = path.basename(resolved);
  const size = fs.statSync(resolved).size;
  const contentType = contentTypeFor(filename);
  const payload = await client().fileUpload(contentType, filename, size);
  const uploadFile =
    payload.uploadFile && payload.uploadFile.then
      ? await payload.uploadFile
      : payload.uploadFile;
  if (!uploadFile || !uploadFile.uploadUrl) {
    throw Object.assign(new Error(`Linear file upload was not prepared for ${filename}`), {
      code: "api",
    });
  }
  await putSignedUpload(
    uploadFile.uploadUrl,
    uploadFile.headers,
    fs.readFileSync(resolved),
    contentType
  );
  const result = await client().createAttachment({
    issueId,
    url: uploadFile.assetUrl,
    title: title || filename,
    subtitle: subtitle || undefined,
  });
  const attachment = await result.attachment;
  return {
    id: attachment?.id,
    url: uploadFile.assetUrl,
    title: title || filename,
    subtitle: subtitle || null,
    filename,
  };
}

async function attachLinksAndFiles(issueId, payload) {
  const attached = [];
  for (const link of asArray(getValue(payload, ["links"]))) {
    if (!link || !link.url) continue;
    const result = await client().createAttachment({
      issueId,
      url: String(link.url),
      title: String(link.title || link.url),
    });
    const attachment = await result.attachment;
    attached.push({
      id: attachment?.id,
      url: String(link.url),
      title: String(link.title || link.url),
    });
  }
  for (const file of asArray(getValue(payload, ["files", "file", "attachments"]))) {
    const spec = typeof file === "string" ? { path: file } : file || {};
    const filePath = spec.path || spec.file || spec.url;
    if (!filePath || String(filePath).startsWith("http")) continue;
    attached.push(await attachFile(issueId, String(filePath), spec.title));
  }
  return attached;
}

async function saveIssue(payload) {
  const linear = client();
  const id = getValue(payload, ["id"]);
  const input = {
    title: getValue(payload, ["title"]),
    description: getValue(payload, ["description"]),
    dueDate: getValue(payload, ["dueDate", "due_date"]),
    estimate: getValue(payload, ["estimate"]),
    priority: getValue(payload, ["priority"]),
    parentId: getValue(payload, ["parentId", "parent_id"]),
    stateId: getValue(payload, ["stateId", "state_id"]),
    cycleId: undefined,
    assigneeId: getValue(payload, ["assigneeId", "assignee_id"]),
  };
  const team = getValue(payload, ["team", "teamId", "team_id"]);
  const project = getValue(payload, ["projectId", "project_id", "project"]);
  const cycle = getValue(payload, ["cycleId", "cycle_id", "cycle"]);
  const state = getValue(payload, ["state"]);
  const assignee = getValue(payload, ["assignee"]);
  const labels = await resolveLabelIds(
    getValue(payload, ["labelIds", "label_ids", "labels", "kind"])
  );
  if (team) input.teamId = await resolveTeamId(team);
  if (project) input.projectId = await resolveProjectId(project);
  if (cycle != null) input.cycleId = await resolveCycleId(cycle);
  if (labels && labels.length) input.labelIds = labels;
  if (state && !input.stateId) input.stateId = state;
  if (assignee === "me") {
    const viewer = await linear.viewer;
    input.assigneeId = viewer.id;
  } else if (assignee && !input.assigneeId) {
    input.assigneeId = assignee;
  }
  Object.keys(input).forEach((key) => input[key] === undefined && delete input[key]);
  let issue;
  if (id) {
    const result = await linear.updateIssue(id, input);
    issue = await result.issue;
  } else {
    if (!input.title || !input.teamId) {
      throw Object.assign(new Error("title and team are required when creating an issue"), {
        code: "usage",
      });
    }
    const result = await linear.createIssue(input);
    issue = await result.issue;
  }
  const serialized = await serializeIssue(issue);
  const attached = await attachLinksAndFiles(issue.id, payload);
  if (attached.length) serialized.attachments = attached;
  return serialized;
}

async function createAttachment(payload) {
  const issueId = getValue(payload, ["issueId", "issue_id", "issue", "id"], {
    required: true,
  });
  const filePath = getValue(payload, ["file", "path"]);
  if (filePath) {
    return attachFile(
      issueId,
      String(filePath),
      getValue(payload, ["title"]),
      getValue(payload, ["subtitle"])
    );
  }
  const url = getValue(payload, ["url"], { required: true });
  const result = await client().createAttachment({
    issueId,
    url: String(url),
    title: String(getValue(payload, ["title"], { defaultValue: url })),
    subtitle: getValue(payload, ["subtitle"]),
  });
  const attachment = await result.attachment;
  return { id: attachment.id, url, title: attachment.title || getValue(payload, ["title"]) };
}

async function attachFileCommand(payload) {
  const issueId = getValue(payload, ["issueId", "issue_id", "issue", "id"], {
    required: true,
  });
  const filePath = getValue(payload, ["file", "path"], { required: true });
  return attachFile(
    issueId,
    String(filePath),
    getValue(payload, ["title"]),
    getValue(payload, ["subtitle"])
  );
}

async function saveCycle(payload) {
  const id = getValue(payload, ["id"], { required: true });
  const input = {
    name: getValue(payload, ["name"]),
    description: getValue(payload, ["description"]),
  };
  Object.keys(input).forEach((key) => input[key] === undefined && delete input[key]);
  const result = await client().updateCycle(id, input);
  const cycle = await result.cycle;
  return {
    id: cycle.id,
    name: cycle.name,
    number: cycle.number,
    startsAt: cycle.startsAt,
    endsAt: cycle.endsAt,
  };
}

async function listComments(payload) {
  const issueId = getValue(payload, ["issueId", "issue_id", "id"], { required: true });
  const issue = await client().issue(issueId);
  const comments = await issue.comments({
    first: Number(getValue(payload, ["limit", "first"], { defaultValue: 50 })),
  });
  return {
    comments: comments.nodes.map((comment) => ({
      id: comment.id,
      body: comment.body,
      createdAt: comment.createdAt,
    })),
  };
}

async function saveComment(payload) {
  const id = getValue(payload, ["id"]);
  const body = getValue(payload, ["body"], { required: !id });
  const issueId = getValue(payload, ["issueId", "issue_id"]);
  const linear = client();
  if (id) {
    const result = await linear.updateComment(id, { body });
    const comment = await result.comment;
    return { id: comment.id, body: comment.body };
  }
  const result = await linear.createComment({ body, issueId });
  const comment = await result.comment;
  return { id: comment.id, body: comment.body };
}

async function deleteComment(payload) {
  const id = getValue(payload, ["id"], { required: true });
  await client().deleteComment(id);
  return { id, deleted: true };
}

const COMMANDS = {
  ping,
  get_workspace: getWorkspace,
  list_teams: listTeams,
  get_team: getTeam,
  list_users: listUsers,
  get_user: getUser,
  list_projects: listProjects,
  get_project: getProject,
  save_project: saveProject,
  list_issue_statuses: listIssueStatuses,
  get_issue_status: getIssueStatus,
  list_issue_labels: listIssueLabels,
  create_issue_label: createIssueLabel,
  list_cycles: listCycles,
  save_cycle: saveCycle,
  list_milestones: listMilestones,
  get_milestone: getMilestone,
  save_milestone: saveMilestone,
  list_issues: listIssues,
  all_issues: allIssues,
  current_cycle_issues: currentCycleIssues,
  now,
  get_issue: getIssue,
  save_issue: saveIssue,
  create_attachment: createAttachment,
  attach_file: attachFileCommand,
  list_comments: listComments,
  save_comment: saveComment,
  delete_comment: deleteComment,
};

async function main() {
  const { command, payload } = parseInvocation(process.argv);
  try {
    if (command === "commands" || command === "help") {
      emit({
        ok: true,
        command: "commands",
        data: {
          program: "linear",
          commands: ["commands", ...Object.keys(COMMANDS)].filter((value, index, all) => all.indexOf(value) === index).sort(),
          invoke: [
            'python tools/run_tool/run_tool.py linear commands',
            'python tools/run_tool/run_tool.py linear list_issues --cycle current',
            "Always use flags. Never write scratch files.",
          ],
        },
      });
      return 0;
    }
    const handler = COMMANDS[command];
    if (!handler) {
      const known = ["commands", ...Object.keys(COMMANDS)].sort();
      throw Object.assign(
        new Error(
          `Unknown command: ${command}. Known: ${known.join(", ")}. Example: python tools/run_tool/run_tool.py linear list_issues --cycle current`
        ),
        { code: "usage" }
      );
    }
    const data = await handler(payload);
    emit({ ok: true, command, data });
    return 0;
  } catch (error) {
    emit(
      {
        ok: false,
        command,
        error: { code: error.code || "api", message: error.message || String(error) },
      },
      true
    );
    return 1;
  }
}

if (require.main === module) {
  main().then((code) => process.exit(code));
}

module.exports = {
  normalizeLabelIds,
  parseFlagValue,
  parseInvocation,
  assignFlag,
  getValue,
  keyVariants,
  cycleFilter,
  cycleRelativeFilter,
  cycleNamedFilter,
  serializeCycle,
  localClock,
};
