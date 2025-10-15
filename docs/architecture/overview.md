# Architecture Overview

The Modularity is a polymorphic service architecture enabling applications to operate in multiple deployment modes.

## Core Concepts

### Deployment Modes

- **Standalone** - Runs as independent microservice
- **Embedded** - Loads as in-process module
- **Distributed** - Service mesh with discovery

### Components

- **SDK** - Developer libraries (Python, JS, Go, Rust, Ruby)
- **Registry** - Service discovery and health monitoring
- **CLI** - Management and deployment tools

## Design Philosophy

Write once, deploy anywhere. Business logic separated from deployment topology.

[More details to come]
