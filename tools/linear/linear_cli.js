#!/usr/bin/env node
"use strict";

const fs = require("fs");
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

function getValue(payload, names, options = {}) {
  const { required = false, defaultValue = undefined } = options;
  for (const name of names) {
    for (const candidate of [name, toSnake(name), toCamel(name)]) {
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
      // PowerShell may strip JSON quotes, leaving [uuid] instead of ["uuid"].
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
  if (args.length === 0 || args.includes("--help") || args.includes("-h")) {
    return { command: "commands", payload: {} };
  }
  const command = args[0];
  const payload = {};
  let jsonIndex = args.indexOf("--json");
  if (jsonIndex >= 0 && args[jsonIndex + 1]) {
    Object.assign(payload, JSON.parse(args[jsonIndex + 1]));
  }
  const jsonFileIndex = args.indexOf("--json-file");
  if (jsonFileIndex >= 0 && args[jsonFileIndex + 1]) {
    Object.assign(
      payload,
      JSON.parse(fs.readFileSync(args[jsonFileIndex + 1], "utf8"))
    );
  }
  let key = null;
  for (let index = 1; index < args.length; index += 1) {
    const token = args[index];
    if (token === "--json" || token === "--json-file") {
      index += 1;
      continue;
    }
    if (token.startsWith("--") && token.includes("=")) {
      const [name, value] = token.slice(2).split("=");
      payload[name] = parseFlagValue(value);
      key = null;
      continue;
    }
    if (token.startsWith("--")) {
      key = token.slice(2);
      continue;
    }
    if (!key) {
      throw Object.assign(new Error(`Unexpected argument: ${token}`), {
        code: "usage",
      });
    }
    payload[key] = parseFlagValue(token);
    key = null;
  }
  if (key) payload[key] = true;
  return { command, payload };
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
    cycle: cycle ? { id: cycle.id, name: cycle.name, number: cycle.number } : null,
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

async function listCycles(payload) {
  const teamId = getValue(payload, ["team", "teamId", "id"], { required: true });
  const team = await client().team(teamId);
  const cycles = await team.cycles({
    first: Number(getValue(payload, ["limit", "first"], { defaultValue: 50 })),
  });
  return {
    cycles: cycles.nodes.map((cycle) => ({
      id: cycle.id,
      name: cycle.name,
      number: cycle.number,
      startsAt: cycle.startsAt,
      endsAt: cycle.endsAt,
    })),
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
  if (cycle) filter.cycle = { or: [{ id: { eq: cycle } }, { name: { eq: cycle } }] };
  if (assignee === "me") filter.assignee = { isMe: { eq: true } };
  else if (assignee === null) filter.assignee = { null: true };
  else if (assignee) filter.assignee = { or: [{ id: { eq: assignee } }, { email: { eq: assignee } }, { name: { eq: assignee } }] };
  if (parentId) filter.parent = { or: [{ id: { eq: parentId } }, { identifier: { eq: parentId } }] };
  if (priority !== undefined) filter.priority = { eq: Number(priority) };
  return Object.keys(filter).length ? filter : undefined;
}

async function listIssues(payload) {
  const connection = await client().issues({
    first: Number(getValue(payload, ["limit", "first"], { defaultValue: 50 })),
    after: getValue(payload, ["cursor", "after"]),
    filter: issueFilter(payload),
    includeArchived: Boolean(getValue(payload, ["includeArchived", "include_archived"], { defaultValue: false })),
  });
  const fields = getValue(payload, ["fields"]);
  return {
    issues: await Promise.all(connection.nodes.map((issue) => serializeIssue(issue, fields))),
    pageInfo: pageInfo(connection),
  };
}

async function getIssue(payload) {
  const id = getValue(payload, ["id"], { required: true });
  const issue = await client().issue(id);
  return serializeIssue(issue);
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
    projectId: getValue(payload, ["projectId", "project_id", "project"]),
    stateId: getValue(payload, ["stateId", "state_id"]),
    cycleId: getValue(payload, ["cycleId", "cycle_id"]),
    assigneeId: getValue(payload, ["assigneeId", "assignee_id"]),
  };
  const team = getValue(payload, ["team", "teamId", "team_id"]);
  const state = getValue(payload, ["state"]);
  const assignee = getValue(payload, ["assignee"]);
  const labels = normalizeLabelIds(getValue(payload, ["labelIds", "label_ids", "labels"]));
  if (team) input.teamId = team;
  if (labels && labels.length) input.labelIds = labels;
  if (state && !input.stateId) input.stateId = state;
  if (assignee === "me") {
    const viewer = await linear.viewer;
    input.assigneeId = viewer.id;
  } else if (assignee && !input.assigneeId) {
    input.assigneeId = assignee;
  }
  Object.keys(input).forEach((key) => input[key] === undefined && delete input[key]);
  if (id) {
    const result = await linear.updateIssue(id, input);
    return serializeIssue(await result.issue);
  }
  if (!input.title || !input.teamId) {
    throw Object.assign(new Error("title and team are required when creating an issue"), {
      code: "usage",
    });
  }
  const result = await linear.createIssue(input);
  return serializeIssue(await result.issue);
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
  list_milestones: listMilestones,
  get_milestone: getMilestone,
  save_milestone: saveMilestone,
  list_issues: listIssues,
  get_issue: getIssue,
  save_issue: saveIssue,
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
            ".\\tools\\run-tool\\run-tool.ps1 linear <command> [flags]",
            "python tools/run-tool/run_tool.py linear <command> [flags]",
          ],
          shell: "powershell",
          rule: "Use Windows PowerShell or a real python.exe. Do not wrap PowerShell cmdlets in bash -c. Do not use pyodide or any emulated interpreter.",
        },
      });
      return 0;
    }
    const handler = COMMANDS[command];
    if (!handler) {
      const known = ["commands", ...Object.keys(COMMANDS)].sort();
      throw Object.assign(
        new Error(
          `Unknown command: ${command}. Known: ${known.join(", ")}. Discover commands with commands or --help.`
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
};
