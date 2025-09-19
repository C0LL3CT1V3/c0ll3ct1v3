# C0ll3CT1V3 Business Management System

A comprehensive business management platform for tracking bank accounts, crypto wallets, ledgers, and business documents.

## Features

- **Bank Account Management**: Track multiple bank accounts with balances
- **Crypto Wallet Management**: Manage cryptocurrency holdings
- **Ledger System**: Track assets and liabilities
- **Document Management**: Store and organize business documents

## Quick Start

### Backend (Python/FastAPI)

1. Navigate to backend directory:
   ```bash
   cd src/c0ll3ct1v3/backend
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the server:
   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`

### Frontend (React)

1. Navigate to frontend directory:
   ```bash
   cd src/c0ll3ct1v3/frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm start
   ```

The frontend will be available at `http://localhost:3000`

### Using Docker Compose

1. Navigate to shared directory:
   ```bash
   cd src/c0ll3ct1v3/shared
   ```

2. Start both services:
   ```bash
   docker-compose up
   ```

## API Endpoints

- `GET /` - API health check
- `GET /health` - Health status
- `GET /accounts/` - List all bank accounts
- `POST /accounts/` - Create new bank account
- `GET /accounts/{id}` - Get specific account

## Project Structure

- `backend/` - Python FastAPI backend
- `frontend/` - React frontend
- `shared/` - Docker configuration and shared files
