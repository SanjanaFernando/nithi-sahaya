"use strict";

const API_BASE = document.documentElement.dataset.apiBase || "http://127.0.0.1:8000";
const form = document.querySelector("#ask-form");
const questionInput = document.querySelector("#question");
const languageInput = document.querySelector("#language");
const sendButton = document.querySelector("#send-button");
const charCount = document.querySelector("#char-count");
const messages = document.querySelector("#messages");
const starters = document.querySelector("#starter-area");

function escapeText(value) {
  return String(value ?? "");
}

function appendUserMessage(question) {
  const bubble = document.createElement("div");
  bubble.className = "user-message";
  bubble.textContent = question;
  messages.append(bubble);
}

function makeSourcePanel(records) {
  const panel = document.createElement("section");
  panel.className = "source-panel";
  panel.setAttribute("aria-label", "Sources used for this answer");
  const heading = document.createElement("h3");
  heading.textContent = "Sources used in this answer";
  panel.append(heading);

  const seen = new Set();
  for (const record of records) {
    if (!record || typeof record.id !== "string" || seen.has(record.id)) continue;
    seen.add(record.id);
    const card = document.createElement("article");
    card.className = "source-card";
    card.dataset.sourceId = record.id;
    const title = document.createElement("h4");
    title.textContent = `${escapeText(record.act_name || record.source_file || "Source")} · Section ${escapeText(record.section_number || "")}`;
    const subtitle = document.createElement("p");
    subtitle.className = "source-subtitle";
    subtitle.textContent = `${escapeText(record.source_file || "")} · page ${escapeText(record.source_page ?? "not listed")}`;
    const quote = document.createElement("blockquote");
    quote.textContent = escapeText(record.text || "Section text was not included in the API response.");
    card.append(title, subtitle, quote);
    panel.append(card);
  }
  return panel;
}

function renderAnswer(answerNode, answer, records) {
  const sourceIds = new Set(records.map((item) => item && item.id).filter((id) => typeof id === "string"));
  const citationPattern = /\[CITE:([^\]]+)\]/g;
  const headingPattern = /(^|\n)(A\. Simple answer|B\. Legal basis|C\. What to do next)(?=\n|$)/g;
  const appendText = (value) => {
    let textCursor = 0;
    let headingMatch;
    headingPattern.lastIndex = 0;
    while ((headingMatch = headingPattern.exec(value)) !== null) {
      const headingStart = headingMatch.index + headingMatch[1].length;
      answerNode.append(document.createTextNode(value.slice(textCursor, headingStart)));
      const heading = document.createElement("strong");
      heading.className = "answer-heading";
      heading.textContent = headingMatch[2];
      answerNode.append(heading);
      textCursor = headingPattern.lastIndex;
    }
    answerNode.append(document.createTextNode(value.slice(textCursor)));
  };
  let cursor = 0;
  let match;
  while ((match = citationPattern.exec(answer)) !== null) {
    appendText(answer.slice(cursor, match.index));
    const id = match[1];
    if (sourceIds.has(id)) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "citation-link";
      const sourceRecord = records.find((item) => item && item.id === id);
      button.textContent = `§ ${(sourceRecord && sourceRecord.section_number) || "Source"}`;
      button.setAttribute("aria-label", `Show cited section ${button.textContent}`);
      button.addEventListener("click", () => {
        const message = answerNode.closest(".assistant-message");
        const panel = message && message.querySelector(".source-panel");
        const sourceCards = panel ? Array.from(panel.querySelectorAll(".source-card")) : [];
        const card = sourceCards.find((item) => item.dataset.sourceId === id);
        if (!panel || !card) return;
        panel.classList.add("open");
        try { card.scrollIntoView({ behavior: "smooth", block: "center" }); }
        catch { card.scrollIntoView(); }
        card.classList.add("highlight");
        window.setTimeout(() => card.classList.remove("highlight"), 1500);
      });
      answerNode.append(button);
    } else {
      // Never present an ID as a valid citation unless the API returned its source.
      answerNode.append(document.createTextNode("[citation unavailable]"));
    }
    cursor = citationPattern.lastIndex;
  }
  appendText(answer.slice(cursor));
}

function addAssistantMessage({ answer = "", records = [], refused = false, reason = "", retryQuestion = "", retryLanguage = "English" }) {
  const article = document.createElement("article");
  article.className = "assistant-message";
  const header = document.createElement("div");
  header.className = "assistant-header";
  const avatar = document.createElement("span");
  avatar.className = "assistant-avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = "නී";
  const name = document.createElement("div");
  const strong = document.createElement("strong");
  strong.textContent = "Nithi Sahaya";
  const small = document.createElement("small");
  small.textContent = "AI-generated information · check current law";
  name.append(strong, small);
  header.append(avatar, name);

  const answerNode = document.createElement("div");
  answerNode.className = "assistant-answer";
  renderAnswer(answerNode, answer, records);
  const meta = document.createElement("div");
  meta.className = "answer-meta";
  if (refused) {
    const refusal = document.createElement("span");
    refusal.className = "refusal-label";
    refusal.textContent = reason === "corpus_update_required" ? "Source needs an update" : "Unable to answer safely";
    meta.append(refusal);
  } else {
    const feedback = document.createElement("div");
    feedback.className = "feedback";
    feedback.append(document.createTextNode("Was this helpful?"));
    for (const [label, symbol] of [["Yes", "👍"], ["No", "👎"]]) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = symbol;
      button.setAttribute("aria-label", label === "Yes" ? "This answer was helpful" : "This answer was not helpful");
      button.addEventListener("click", () => {
        feedback.replaceChildren();
        const note = document.createElement("span");
        note.className = "feedback-note";
        note.textContent = "Thanks. This feedback is not sent or saved.";
        feedback.append(note);
      }, { once: true });
      feedback.append(button);
    }
    meta.append(feedback);
  }
  const sourcePanel = makeSourcePanel(records);
  if (records.length) {
    const sourceToggle = document.createElement("button");
    sourceToggle.type = "button";
    sourceToggle.className = "source-toggle";
    sourceToggle.setAttribute("aria-expanded", "false");
    sourceToggle.textContent = `View source text (${new Set(records.map((record) => record && record.id).filter(Boolean)).size})`;
    sourceToggle.addEventListener("click", () => {
      sourcePanel.classList.toggle("open");
      sourceToggle.setAttribute("aria-expanded", String(sourcePanel.classList.contains("open")));
      sourceToggle.textContent = `${sourcePanel.classList.contains("open") ? "Hide" : "View"} source text (${new Set(records.map((record) => record && record.id).filter(Boolean)).size})`;
    });
    meta.append(sourceToggle);
  }
  if (reason === "service_error" && retryQuestion) {
    const retryButton = document.createElement("button");
    retryButton.type = "button";
    retryButton.className = "retry-button";
    retryButton.textContent = "Try again";
    retryButton.addEventListener("click", () => ask(retryQuestion, retryLanguage, false), { once: true });
    meta.append(retryButton);
  }
  article.append(header, answerNode, meta, sourcePanel);
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
      state.refused = Boolean(metadata.refused);
      state.reason = typeof metadata.reason === "string" ? metadata.reason : "";
    } catch {
      throw new Error("The answer service returned invalid source information.");
    }
  } else if (data === "[DONE]") {
    state.done = true;
  } else if (data) {
    try {
      const message = JSON.parse(data);
      if (typeof message.text === "string") state.answer += message.text;
    } catch {
      throw new Error("The answer service returned an unreadable response.");
    }
  }
}

async function ask(question, language, addUserBubble = true) {
  if (addUserBubble) appendUserMessage(question);
  const loading = document.createElement("article");
  loading.className = "assistant-message";
  loading.innerHTML = '<div class="assistant-header"><span class="assistant-avatar" aria-hidden="true">නී</span><div><strong>Nithi Sahaya</strong><small>Checking the source sections…</small></div></div><span class="typing-indicator" aria-label="Loading"><i></i><i></i><i></i></span>';
  messages.append(loading);
  const loadingMessage = loading.querySelector(".assistant-header small");
  const slowRequestTimer = window.setTimeout(() => {
    if (loadingMessage) loadingMessage.textContent = "Gemini is taking longer than expected. This request will time out automatically.";
  }, 8000);
  starters.hidden = true;
  sendButton.disabled = true;

  try {
    const response = await fetch(`${API_BASE.replace(/\/$/, "")}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ question, language }),
    });
    if (!response.ok) {
      let detail = "The answer service is unavailable. Please try again shortly.";
      try {
        const body = await response.json();
        if (response.status === 429) detail = "Too many questions in a short time. Wait a moment, then try again.";
        else if (response.status === 422) detail = "Please enter a question between 2 and 4,000 characters.";
        else if (response.status === 503) detail = "The answer service is temporarily unavailable. Check back shortly.";
        else if (typeof body.detail === "string") detail = body.detail;
      } catch { /* Keep the safe generic message. */ }
      throw new Error(detail);
    }
    const state = { answer: "", records: [], refused: false, reason: "", done: false };
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
    if (!state.answer) throw new Error("The answer service returned an empty response. Please try again.");
    loading.remove();
    addAssistantMessage(state);
  } catch (error) {
    loading.remove();
    addAssistantMessage({ answer: error instanceof Error ? error.message : "The service could not complete this request.", records: [], refused: true, reason: "service_error", retryQuestion: question, retryLanguage: language });
  } finally {
    window.clearTimeout(slowRequestTimer);
    sendButton.disabled = false;
    questionInput.focus();
    messages.scrollIntoView({ behavior: "smooth", block: "end" });
  }
}

if (form) form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (question.length < 2 || question.length > 4000 || sendButton.disabled) return;
  const language = languageInput.value;
  questionInput.value = "";
  charCount.textContent = "0 / 4000";
  ask(question, language);
});

if (questionInput) questionInput.addEventListener("input", () => {
  charCount.textContent = `${questionInput.value.length} / 4000`;
});

document.querySelectorAll(".starter-card").forEach((button) => {
  button.addEventListener("click", () => {
    questionInput.value = button.dataset.question || "";
    charCount.textContent = `${questionInput.value.length} / 4000`;
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
