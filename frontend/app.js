"use strict";

// The production API URL is set on <html data-api-base>. A page served from this machine talks to a local API.
const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1"]);
const API_BASE = (LOCAL_HOSTS.has(window.location.hostname)
  ? "http://127.0.0.1:8000"
  : document.documentElement.dataset.apiBase || "").replace(/\/$/, "");
// Covers a cold start on the free host plus one answer and one stricter retry on the server.
const REQUEST_TIMEOUT_MS = 180000;
const MAX_QUESTION_LENGTH = 4000;
const ANSWER_LANG = { English: "en", Sinhala: "si", Tamil: "ta" };
const GENERIC_ERROR = "We couldn't prepare an answer just now. Please try again.";
const form = document.querySelector("#ask-form");
const questionInput = document.querySelector("#question");
const languageInput = document.querySelector("#language");
const sendButton = document.querySelector("#send-button");
const charCount = document.querySelector("#char-count");
const messages = document.querySelector("#messages");
const starters = document.querySelector("#starter-area");
const formError = document.querySelector("#form-error");

function asText(value) {
  return String(value ?? "");
}

function appendUserMessage(question) {
  const bubble = document.createElement("div");
  bubble.className = "user-message";
  bubble.textContent = question;
  messages.append(bubble);
}

function makeSourcePanel(records, webSources = []) {
  const panel = document.createElement("section");
  panel.className = "source-panel";
  panel.setAttribute("aria-label", "References for this answer");
  const heading = document.createElement("h3");
  heading.textContent = "References for this answer";
  panel.append(heading);

  const seen = new Set();
  for (const record of records) {
    if (!record || typeof record.id !== "string" || seen.has(record.id)) continue;
    seen.add(record.id);
    // Each reference is its own dropdown: the title is always visible, the section text expands.
    const card = document.createElement("details");
    card.className = "source-card";
    card.dataset.sourceId = record.id;
    const summary = document.createElement("summary");
    const title = document.createElement("h4");
    title.textContent = `${asText(record.act_name || "Legal document")} · Section ${asText(record.section_number || "")}`;
    const subtitle = document.createElement("p");
    subtitle.className = "source-subtitle";
    subtitle.textContent = `Source PDF · page ${asText(record.source_page ?? "not listed")}`;
    summary.append(title, subtitle);
    const quote = document.createElement("blockquote");
    quote.textContent = asText(record.text || "This section text is not available.");
    card.append(summary, quote);
    panel.append(card);
  }
  if (webSources.length) {
    const webHeading = document.createElement("h3");
    webHeading.textContent = "Online references";
    panel.append(webHeading);
    for (const source of webSources) {
      if (!source || typeof source.url !== "string" || !/^https?:\/\//i.test(source.url)) continue;
      const link = document.createElement("a");
      link.className = "web-source-link";
      link.href = source.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = typeof source.title === "string" && source.title ? source.title : source.url;
      panel.append(link);
    }
  }
  return panel;
}

function renderAnswer(answerNode, answer, records, webSources = []) {
  const sourceIds = new Set(records.map((item) => item && item.id).filter((id) => typeof id === "string"));
  const sourceUrls = new Map(webSources.filter((item) => item && typeof item.url === "string").map((item) => [item.url, item]));
  const citationPattern = /\[(CITE|WEB):([^\]]+)\]/g;
  const headingPattern = /(^|\n)(A\. Simple answer|B\. Legal basis|C\. What to do next)(?=\n|$)/g;
  const friendlyHeadings = { "A. Simple answer": "Short answer", "B. Legal basis": "What the law says", "C. What to do next": "What you can do" };
  const appendText = (value) => {
    let textCursor = 0;
    let headingMatch;
    headingPattern.lastIndex = 0;
    while ((headingMatch = headingPattern.exec(value)) !== null) {
      const headingStart = headingMatch.index + headingMatch[1].length;
      answerNode.append(document.createTextNode(value.slice(textCursor, headingStart)));
      const heading = document.createElement("strong");
      heading.className = "answer-heading";
      heading.textContent = friendlyHeadings[headingMatch[2]] || headingMatch[2];
      answerNode.append(heading);
      textCursor = headingPattern.lastIndex;
    }
    answerNode.append(document.createTextNode(value.slice(textCursor)));
  };
  let cursor = 0;
  let match;
  while ((match = citationPattern.exec(answer)) !== null) {
    appendText(answer.slice(cursor, match.index));
    const kind = match[1];
    const id = match[2];
    if (kind === "CITE" && sourceIds.has(id)) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "citation-link";
      const sourceRecord = records.find((item) => item && item.id === id);
      button.textContent = `§ ${(sourceRecord && sourceRecord.section_number) || "Source"}`;
      button.setAttribute("aria-label", `Show the cited section ${button.textContent}`);
      button.addEventListener("click", () => {
        const message = answerNode.closest(".assistant-message");
        const panel = message && message.querySelector(".source-panel");
        const sourceCards = panel ? Array.from(panel.querySelectorAll(".source-card")) : [];
        const card = sourceCards.find((item) => item.dataset.sourceId === id);
        if (!panel || !card) return;
        panel.classList.add("open");
        const toggle = message.querySelector(".source-toggle");
        if (toggle) {
          toggle.setAttribute("aria-expanded", "true");
          toggle.textContent = toggle.textContent.replace(/^View/, "Hide");
        }
        card.open = true;
        try { card.scrollIntoView({ behavior: "smooth", block: "center" }); }
        catch { card.scrollIntoView(); }
        card.classList.add("highlight");
        window.setTimeout(() => card.classList.remove("highlight"), 1500);
      });
      answerNode.append(button);
    } else if (kind === "WEB" && sourceUrls.has(id)) {
      const link = document.createElement("a");
      link.className = "citation-link web-citation-link";
      link.href = id;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = "Open reference";
      link.setAttribute("aria-label", `Open reference: ${sourceUrls.get(id).title || id}`);
      answerNode.append(link);
    } else {
      // Never present an ID as a valid citation unless the API returned its source.
      answerNode.append(document.createTextNode("[source unavailable]"));
    }
    cursor = citationPattern.lastIndex;
  }
  appendText(answer.slice(cursor));
}

function addAssistantMessage({ answer = "", records = [], web_sources = [], refused = false, reason = "", language = "English", retryQuestion = "" }) {
  const article = document.createElement("article");
  article.className = "assistant-message";
  const header = document.createElement("div");
  header.className = "assistant-header";
  const avatar = document.createElement("img");
  avatar.className = "assistant-avatar";
  avatar.src = "favicon.svg";
  avatar.alt = "";
  avatar.width = 34;
  avatar.height = 34;
  const name = document.createElement("div");
  const strong = document.createElement("strong");
  strong.textContent = "SriLaw AI";
  const small = document.createElement("small");
  small.textContent = "AI-generated information · check current law";
  name.append(strong, small);
  header.append(avatar, name);

  const answerNode = document.createElement("div");
  answerNode.className = "assistant-answer";
  if (reason !== "service_error") answerNode.lang = ANSWER_LANG[language] || "en";
  renderAnswer(answerNode, answer, records, web_sources);
  const meta = document.createElement("div");
  meta.className = "answer-meta";
  const actions = document.createElement("div");
  actions.className = "answer-actions";
  if (refused) {
    const refusal = document.createElement("span");
    refusal.className = "refusal-label";
    refusal.textContent = reason === "corpus_update_required" ? "This source may need an update" : reason === "emergency_safety_concern" ? "Get urgent help" : "Please check with an official source";
    meta.append(refusal);
  }
  const sourcePanel = makeSourcePanel(records, web_sources);
  if (records.length || web_sources.length) {
    const sourceCount = new Set(records.map((record) => record && record.id).filter(Boolean)).size + web_sources.length;
    const sourceToggle = document.createElement("button");
    sourceToggle.type = "button";
    sourceToggle.className = "source-toggle";
    sourceToggle.setAttribute("aria-expanded", "false");
    sourceToggle.textContent = `View references (${sourceCount})`;
    sourceToggle.addEventListener("click", () => {
      sourcePanel.classList.toggle("open");
      sourceToggle.setAttribute("aria-expanded", String(sourcePanel.classList.contains("open")));
      sourceToggle.textContent = `${sourcePanel.classList.contains("open") ? "Hide" : "View"} references (${sourceCount})`;
    });
    actions.append(sourceToggle);
  }
  if (reason === "service_error" && retryQuestion) {
    const retryButton = document.createElement("button");
    retryButton.type = "button";
    retryButton.className = "retry-button";
    retryButton.textContent = "Try again";
    retryButton.addEventListener("click", () => {
      article.remove();
      ask(retryQuestion, language, false);
    }, { once: true });
    actions.append(retryButton);
  }
  if (actions.childElementCount) meta.append(actions);
  article.append(header, answerNode);
  if (meta.childElementCount) article.append(meta);
  article.append(sourcePanel);
  messages.append(article);
  return article;
}

function parseEvent(block, state) {
  if (!block.trim()) return;
  let event = "message";
  const dataLines = [];
  for (const line of block.split(/\r?\n/)) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
  }
  const data = dataLines.join("\n");
  if (event === "metadata") {
    try {
      const metadata = JSON.parse(data);
      state.records = Array.isArray(metadata.sources) ? metadata.sources : [];
      state.web_sources = Array.isArray(metadata.web_sources) ? metadata.web_sources : [];
      state.refused = Boolean(metadata.refused);
      state.reason = typeof metadata.reason === "string" ? metadata.reason : "";
    } catch {
      throw new Error(GENERIC_ERROR);
    }
  } else if (data === "[DONE]") {
    state.done = true;
  } else if (data) {
    try {
      const message = JSON.parse(data);
      if (typeof message.text === "string") state.answer += message.text;
    } catch {
      throw new Error(GENERIC_ERROR);
    }
  }
}

async function ask(question, language, addUserBubble = true) {
  if (addUserBubble) appendUserMessage(question);
  const loading = document.createElement("article");
  loading.className = "assistant-message";
  loading.innerHTML = '<div class="assistant-header"><img class="assistant-avatar" src="favicon.svg" alt="" width="34" height="34"><div><strong>SriLaw AI</strong><small>Searching the law and current sources</small></div></div><div class="loading-state" role="status"><span class="loading-spinner" aria-hidden="true"></span><span class="loading-copy">Finding relevant law and preparing your answer</span></div>';
  messages.append(loading);
  const loadingMessage = loading.querySelector(".loading-copy");
  const slowRequestTimer = window.setTimeout(() => {
    if (loadingMessage) loadingMessage.textContent = "This is taking a little longer. The service may be starting up; please keep waiting.";
  }, 8000);
  const controller = new AbortController();
  const timeoutTimer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  starters.hidden = true;
  sendButton.disabled = true;
  messages.setAttribute("aria-busy", "true");

  try {
    let response;
    try {
      response = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify({ question, language }),
        signal: controller.signal,
      });
    } catch (networkError) {
      throw new Error(networkError && networkError.name === "AbortError"
        ? "The answer took too long. Please try again, or ask a shorter question."
        : "We couldn't reach the answer service. Check your connection and try again.");
    }
    if (!response.ok) {
      const messagesByStatus = {
        422: "Please enter a question between 2 and 4,000 characters.",
        429: "Too many questions in a short time. Wait a minute, then try again.",
      };
      throw new Error(messagesByStatus[response.status] || "We couldn't get your answer just now. Please try again shortly.");
    }
    const state = { answer: "", records: [], web_sources: [], refused: false, reason: "", done: false };
    if (response.body && typeof response.body.getReader === "function" && typeof TextDecoder !== "undefined") {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (!state.done) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split(/\r?\n\r?\n/);
        buffer = blocks.pop() || "";
        for (const block of blocks) parseEvent(block, state);
      }
      buffer += decoder.decode();
      if (buffer.trim()) parseEvent(buffer, state);
    } else {
      const fullResponse = await response.text();
      for (const block of fullResponse.replace(/\r\n/g, "\n").split("\n\n")) parseEvent(block, state);
    }
    if (!state.answer) throw new Error(GENERIC_ERROR);
    loading.remove();
    addAssistantMessage({ ...state, language });
  } catch (error) {
    loading.remove();
    const message = error instanceof Error && error.name !== "AbortError" ? error.message : "The answer took too long. Please try again.";
    addAssistantMessage({ answer: message, refused: true, reason: "service_error", language, retryQuestion: question });
  } finally {
    window.clearTimeout(slowRequestTimer);
    window.clearTimeout(timeoutTimer);
    messages.removeAttribute("aria-busy");
    sendButton.disabled = false;
    questionInput.focus();
    messages.scrollIntoView({ behavior: "smooth", block: "end" });
  }
}

if (form) form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (sendButton.disabled) return;
  const question = questionInput.value.trim();
  if (question.length < 2 || question.length > MAX_QUESTION_LENGTH) {
    showFormError(question.length < 2 ? "Please type your question first." : "Please shorten your question to 4,000 characters or fewer.");
    return;
  }
  showFormError("");
  questionInput.value = "";
  updateCharCount();
  ask(question, languageInput.value);
});

function showFormError(message) {
  formError.textContent = message;
  formError.hidden = !message;
  questionInput.setAttribute("aria-invalid", String(Boolean(message)));
}

function updateCharCount() {
  charCount.textContent = `${questionInput.value.length} / ${MAX_QUESTION_LENGTH}`;
}

if (questionInput) questionInput.addEventListener("input", () => {
  updateCharCount();
  if (!formError.hidden) showFormError("");
});

document.querySelectorAll(".starter-card").forEach((button) => {
  button.addEventListener("click", () => {
    questionInput.value = button.dataset.question || "";
    updateCharCount();
    showFormError("");
    questionInput.focus();
  });
});

if (questionInput) questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    if (typeof form.requestSubmit === "function") form.requestSubmit();
    else form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  }
});
