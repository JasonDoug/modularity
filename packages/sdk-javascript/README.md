# Ecosystem SDK - JavaScript

JavaScript/Node.js implementation of the Ecosystem SDK.

## Installation

```bash
npm install @ecosystem/sdk
```

## Usage

```javascript
const { EcosystemSDK } = require('@ecosystem/sdk');

// Load SDK
const sdk = new EcosystemSDK('app.manifest.json');
await sdk.init();

// Run standalone
await sdk.runStandalone();

// Or load as module
const module = await sdk.loadAsModule(config);
```

## Development

```bash
npm install
npm test
npm run lint
```
