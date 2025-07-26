# Consulting Manager API

This document describes the RESTful API for the Consulting Manager project. The API provides programmatic access to project data, timelines, and unified timeline visualizations for integration with external tools and visualizers.

## Overview

- **Base URL:** `/api/`
- **Framework:** Django REST Framework
- **Authentication:** (Optional, see below)

## Authentication

By default, the API is open for development. For production, it is recommended to enable authentication (e.g., Token or Session authentication) and set appropriate permissions.

## Endpoints

### 1. Project Timeline
- **List all projects:**
  - `GET /api/projects/`
- **Retrieve a single project timeline:**
  - `GET /api/projects/<id>/`
- **Retrieve timeline data for a project:**
  - `GET /api/projects/<id>/timeline/`

#### Example Response
```json
{
  "events": [
    {
      "event_id": "milestone_start_1",
      "event_type": "milestone",
      "timestamp": 1712345678,
      "metadata": {
        "title": "Start: Project X",
        "category": "project_start",
        "priority": "high",
        "confidence": 1.0,
        "intended_color": "#3B82F6",
        "actual_color": "#10B981"
      }
    }
  ],
  "correlations": [],
  "metadata": {
    "project_id": 1,
    "generation_time": 1712345678
  }
}
```

### 2. Unified Timeline
- **All projects (aggregated):**
  - `GET /api/unified-timeline/`
- **Single project:**
  - `GET /api/unified-timeline/<project_id>/`

#### Example Response
```json
{
  "events": [ ... ],
  "correlations": [ ... ],
  "metadata": {
    "generation_time": 1712345678,
    "total_projects": 5
  }
}
```

## Error Handling
- Standard HTTP status codes are used (e.g., 200 OK, 404 Not Found).
- Error responses are returned in JSON format.

## Extending the API
- Add new endpoints by creating serializers and views in the `api/` app.
- Register new routes in `api/urls.py`.
- Use Django REST Framework's authentication and permissions for secure access.

## References
- [Django REST Framework Documentation](https://www.django-rest-framework.org/)
- [Consulting Manager Main README](../README.md)

For questions or contributions, see the main project README or contact the maintainers. 