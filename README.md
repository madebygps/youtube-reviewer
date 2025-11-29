# YouTube Reviewer

A web application that uses AI to extract actionable insights from YouTube videos, including key concepts and thesis/argument analysis.

## Prerequisites

- **Python 3.13** - Required for the backend
- **Node.js** - Required for the frontend (Vite/React)
- **.NET SDK** - Required for running with Aspire
- **uv** - Python package manager ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))
- **Azure OpenAI** - Access to an Azure OpenAI resource with a GPT model deployment

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
AZURE_OPENAI_ENDPOINT_GPT5=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY_GPT5=your-api-key
AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5=your-deployment-name
AZURE_OPENAI_ENDPOINT_VERSION_GPT5=2024-02-15-preview
```

| Variable | Description | Required |
|----------|-------------|----------|
| `AZURE_OPENAI_ENDPOINT_GPT5` | Your Azure OpenAI endpoint URL | Yes |
| `AZURE_OPENAI_API_KEY_GPT5` | Your Azure OpenAI API key | Yes |
| `AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5` | The name of your model deployment | Yes |
| `AZURE_OPENAI_ENDPOINT_VERSION_GPT5` | API version (defaults to `2024-02-15-preview`). Check Azure OpenAI documentation for the latest available versions. | No |

## Running the Project

The project uses .NET Aspire to orchestrate both the frontend and backend:

```bash
aspire run
```

This will start both the backend API and the frontend, with proper service discovery and health checks.
