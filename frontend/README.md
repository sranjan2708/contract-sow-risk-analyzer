# Frontend — Contract & SOW Risk Analyzer

This folder hosts the React 18 + Vite single-page application for the Contract & SOW Risk Analyzer.

## Ownership
- **Owner**: Pratyush (Frontend & Client UI)
- All UI state, views, component styling, and routing live here.

## Setup Instructions (for Pratyush)
When scaffolding the Vite application:
1. Open terminal in the `frontend/` directory:
   ```bash
   cd frontend
   npm create vite@latest . -- --template react
   ```
2. When prompted by Vite because files already exist, choose **"Ignore files and continue"** (NEVER choose "Remove existing files").
3. Install dependencies:
   ```bash
   npm install
   npm install react-router-dom
   ```
4. Copy the environment variables:
   ```bash
   cp .env.example .env
   ```
5. Run the dev server:
   ```bash
   npm run dev
   ```

## Architectural Rules
1. **Never call `fetch` directly from components**: All network interactions MUST go through `src/api/endpoints.js` which delegates exclusively to `src/api/client.js`.
2. **Follow Frozen Contracts**: All payload and response fields are strictly `snake_case` matching `shared/contracts.py` and `docs/api_contracts.md`.
3. **No Styling Libraries without Agreement**: Plain CSS only (modular CSS or standard CSS classes), unless both team members explicitly agree otherwise.
