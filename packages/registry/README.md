# Ecosystem Registry Service

Central service discovery and health monitoring.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python registry_service.py
```

Registry will start on http://localhost:5000

## API Endpoints

- `POST /api/register` - Register a service
- `GET /api/services` - List all services
- `GET /api/capabilities/<name>` - Find service by capability
- `GET /health` - Health check

## Development

```bash
pip install -r requirements.txt
pytest
```
