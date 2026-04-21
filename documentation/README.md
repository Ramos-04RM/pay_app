# Documentation Index

This folder contains developer-focused documentation for the Payment Control System.

## Audience
- Primary: middle-level developers
- Secondary: junior developers (extra notes on critical areas)

## How to Use This Folder
1. Start with [Project Overview](./01-project-overview.md)
2. Read [Domain Business Logic](./02-domain-business-logic.md) before touching models or services
3. Use [API Endpoints](./04-api-endpoints.md) for route-level behavior
4. Follow [Development Workflow](./05-development-workflow.md) and [Testing and Quality](./06-testing-and-quality.md) before opening a PR
5. Check [Scaling Guidelines](./07-scaling-guidelines.md) when planning architecture changes
6. Use [Troubleshooting Playbook](./08-troubleshooting-playbook.md) during incidents
7. Use [Internationalization Guide](./09-i18n-localization.md) when updating bilingual UI text

## Document Map
- [**01 - Project Overview**](./01-project-overview.md) - project purpose, stack, and module map
- [**02 - Domain Business Logic**](./02-domain-business-logic.md) - business rules, invariants, and sensitive logic
- [**03 - Architecture and Data Flow**](./03-architecture-and-data-flow.md) - request/data flow and service boundaries
- [**04 - API Endpoints**](./04-api-endpoints.md) - markdown API reference for all key endpoints
- [**05 - Development Workflow**](./05-development-workflow.md) - local setup, migrations, and release workflow
- [**06 - Testing and Quality**](./06-testing-and-quality.md) - test strategy and coverage map
- [**07 - Scaling Guidelines**](./07-scaling-guidelines.md) - scaling and maintainability best practices
- [**08 - Troubleshooting Playbook**](./08-troubleshooting-playbook.md) - operational diagnostics and incident triage
- [**09 - i18n Localization**](./09-i18n-localization.md) - bilingual workflow and `django.mo` build commands

## Critical Security Reminder
Never read, print, or discuss `.env` contents. Use `.env.example` and `.env.security-policy`.
