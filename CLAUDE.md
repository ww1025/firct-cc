# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projects Overview

This repo contains three independent projects:

### 1. 情感分析系统_团队协作版 (Emotion Analysis System)
Streamlit web app for Chinese text emotion classification (6 categories: 开心/愤怒/悲伤/恐惧/惊讶/中性), Zhejiang University themed.

**Start:** Double-click `情感分析系统_团队协作版\启动.bat`
- Kills existing python processes, clears caches, checks model files, starts on `http://localhost:8501`
- UI entry point: `app.py` (Streamlit, import-only from emotion_engine)
- CLI entry point: `predict.py` (interactive REPL with pie chart support)

**Data pipeline:** `merged.csv` → `data_preprocess.py` → `processed_data.npz` → `train_model.py` → `sklearn_emotion_model.pkl` + `tfidf_vectorizer.pkl`

**Architecture:** `emotion_engine.py` is the shared business logic layer — other team members modify this for model/feature work; UI devs import it without touching engine internals.

**Critical pickle compatibility issue:** `train_model.py` was run with sklearn 1.8.0 using `TfidfVectorizer(tokenizer=identity_tokenizer)`. The pickle stores a `__main__.identity_tokenizer` reference. At runtime (sklearn 1.9.0), this fails with `AttributeError`. The fix in `emotion_engine.py` uses `_CompatUnpickler(pickle.Unpickler)` that overrides `find_class()` to intercept `__main__.identity_tokenizer` lookups. **Do NOT replace `_CompatUnpickler(f).load()` with plain `pickle.load(f)` in `load_models()`** — this will break the app.

**Required model files** (in project directory): `sklearn_emotion_model.pkl`, `tfidf_vectorizer.pkl`, `processed_data.npz`

**Streamlit theme config:** `.streamlit\config.toml` forces dark theme with ZJU colors (#003B7B primary, #060E1A background).

### 2. Pomodoro Timer
Electron desktop app — frameless window, system tray, custom tomato icon.

**Start Electron:** Double-click `start-pomodoro.bat` (auto-installs deps then runs `npm start`)
**Start as web app:** `.\launch-pomodoro.ps1` (Edge app mode, or `-Browser` flag for default browser)
- Main process: `main.js` — window management, tray, IPC for minimize/close/always-on-top
- Preload: `preload.js` — secure bridge exposing `window.pomodoro` API
- Renderer: `pomodoro.html`
- Single-instance lock via `app.requestSingleInstanceLock()`

### 3. Flag Scheduling App
Standalone HTML apps: `日常升降旗排班.html` and `index.html` (redirect).

## Temp Files

The repo root contains various temp image files (`temp_screenshot.png`, `temp_image.png`, etc.) and `temp_extract\` — these are debugging artifacts, not production code. `temp_extract\人基大作业\` is a reference copy of the emotion analysis system (correct/working version).

## Git Notes

- Only commit changes inside `情感分析系统_团队协作版\` for the emotion analysis project
- `node_modules\` is gitignored
- Model files (`.pkl`, `.npz`) are large binary files — use Git LFS if sharing
# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

# 识图能力

你的底层模型不具备原生识图能力。遇到图片时，**不要用 Read 工具**，改用 vision.js：

```
node "claude vision/vision.js" "<图片路径>" "用中文描述这张图片"
```

## 触发场景

- 用户分享图片路径（本地或网络 URL）
- 消息中出现 "Saved attachments:" 并列出图片
- 用户要求分析、描述、识别图片内容

## 配置好之后

用户直接发图片，自动识图，无需手动打命令。