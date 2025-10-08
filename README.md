# Agentic WhatsApp Assistant

An intelligent conversational assistant powered by LangGraph and OpenAI, integrated with WhatsApp via Twilio. The assistant can help with weather forecasts, travel planning, and general conversation.

## Features

- 🤖 **AI-Powered Conversations** - Built with LangGraph for structured conversation flows
- 💬 **WhatsApp Integration** - Communicate via WhatsApp using Twilio
- 🌤️ **Weather Information** - Real-time weather data using Google Weather API
- ✈️ **Travel Planning** - Flight and travel assistance (coming soon)
- 🔒 **Safety Features** - Content moderation and rate limiting
- 📊 **Observability** - LangSmith tracing and monitoring
- 🚀 **Production Ready** - Docker support, health checks, and Redis caching

## Architecture

```
┌─────────────┐       ┌──────────────┐       ┌─────────────┐
│   WhatsApp  │──────▶│  FastAPI +   │──────▶│  LangGraph  │
│    User     │◀──────│    Twilio    │◀──────│ Orchestrator│
└─────────────┘       └──────────────┘       └─────────────┘
                                                     │
                                              ┌──────┴──────┐
                                              │             │
                                          ┌───▼───┐   ┌────▼────┐
                                          │Weather│   │ Travel  │
                                          │  Tool │   │  Tool   │
                                          └───────┘   └─────────┘
```

## Prerequisites

- Python 3.11+
- Redis (for session state and caching)
- Twilio account with WhatsApp sandbox/number
- OpenAI API key
- Google Weather API key (optional, for weather features)

## Quick Start

### 1. Clone and Install

```bash
git clone <repository-url>
cd agentic-whatsapp-assistant

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Twilio WhatsApp
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Google Weather API (optional)
GOOGLE_WEATHER_API_KEY=...

# Redis
REDIS_URL=redis://localhost:6379/0

# LangSmith (optional, for tracing)
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=whatsapp-assistant
LANGSMITH_TRACING=true

# Safety
MODERATION_ENABLED=true
TOOL_ALLOWLIST=weather.get
RATE_LIMIT_CHAT_PER_MIN=30
RATE_LIMIT_TOOL_PER_MIN=10
```

### 3. Start Redis

```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or using docker-compose
docker-compose up redis
```

### 4. Run the Application

```bash
# Development mode
make run
# or
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Using Docker Compose (recommended)
docker-compose up
```

The API will be available at `http://localhost:8000`

## WhatsApp Setup with Twilio

### Option 1: Twilio Sandbox (Quick Testing)

1. **Join the Sandbox**
   - Go to [Twilio Console → WhatsApp Sandbox](https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn)
   - Send the join code to the sandbox number (e.g., `join <your-code>`)

2. **Configure Webhook**
   - In Twilio Console, go to WhatsApp Sandbox Settings
   - Set "When a message comes in" to: `https://your-domain.com/webhooks/whatsapp`
   - Method: `POST`
   - Save

3. **Expose Local Server** (for testing)
   ```bash
   # Using ngrok
   ngrok http 8000

   # Use the ngrok HTTPS URL in Twilio webhook settings
   # Example: https://abc123.ngrok.io/webhooks/whatsapp
   ```

4. **Test It**
   - Send a message to your sandbox number
   - Try: "What's the weather in Toronto?"

### Option 2: Production WhatsApp Number

1. **Request WhatsApp Business Profile**
   - Go to Twilio Console → Messaging → Senders
   - Request WhatsApp sender approval
   - Complete Meta Business verification (can take several days)

2. **Configure Webhook**
   - Same as sandbox, but use your production WhatsApp number
   - Webhook: `https://your-production-domain.com/webhooks/whatsapp`

3. **Update Environment**
   ```bash
   TWILIO_WHATSAPP_NUMBER=whatsapp:+your-approved-number
   ```

## API Endpoints

### REST API

- `GET /` - Service information
- `GET /health` - Health check
- `GET /health/ready` - Readiness check (includes Redis)
- `POST /chat` - Send a message (non-streaming)
- `GET /chat/stream` - Stream responses via SSE
- `WebSocket /ws` - WebSocket chat interface
- `POST /webhooks/whatsapp` - Twilio WhatsApp webhook
- `GET /webhooks/whatsapp` - Webhook verification

### Example: REST Chat

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user123",
    "message": "What is the weather like in Paris?"
  }'
```

### Example: Streaming Chat

```bash
curl -N "http://localhost:8000/chat/stream?session_id=user123&message=What%20is%20the%20weather%20in%20Toronto?"
```

## Project Structure

```
.
├── src/
│   ├── api/              # FastAPI routers
│   │   ├── chat.py       # Chat endpoints (REST, SSE, WebSocket)
│   │   ├── health.py     # Health checks
│   │   └── whatsapp.py   # WhatsApp webhook
│   ├── core/             # Core configuration
│   │   ├── config.py     # Settings and environment variables
│   │   ├── tracing.py    # LangSmith integration
│   │   └── http_client.py
│   ├── db/               # Database clients
│   │   └── redis_client.py
│   ├── integrations/     # External service integrations
│   │   ├── twilio_client.py    # Send WhatsApp messages
│   │   └── twilio_security.py  # Webhook signature verification
│   ├── orchestrator/     # LangGraph conversation engine
│   │   ├── graph.py      # Main conversation graph
│   │   ├── nodes.py      # Graph node implementations
│   │   ├── state.py      # Conversation state schema
│   │   ├── router.py     # Intent classification
│   │   ├── extractor.py  # Slot extraction
│   │   └── validators.py # Input validation
│   ├── safety/           # Safety and rate limiting
│   │   ├── moderation.py
│   │   └── rate_limit.py
│   ├── schemas/          # Pydantic models
│   │   ├── chat.py
│   │   ├── weather.py
│   │   └── travel.py
│   ├── tools/            # AI tools
│   │   ├── weather.py    # Weather API integration
│   │   └── toolkit.py    # Tool registry
│   └── main.py           # FastAPI application
├── tests/
│   └── unit/             # Unit tests
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Conversation Flow

The assistant uses a LangGraph state machine to handle conversations:

1. **Setup** - Initialize session from thread_id or session_id
2. **Route Intent** - Classify user intent (WEATHER, TRAVEL, SMALLTALK, OTHER)
3. **Extract Slots** - Extract required information (location, dates, etc.)
4. **Validate** - Check for missing or ambiguous information
5. **Action**:
   - **Ask Question** - Request missing information
   - **Call Tool** - Execute weather/travel API
   - **Generate Response** - Provide final answer

Example conversation:
```
User: What's the weather like?
Bot: Which city should I check the weather for?
User: Toronto
Bot: Toronto on today: Partly cloudy, 18°C.
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/unit/test_whatsapp.py

# Run linting
make lint

# Run type checking
make typecheck

# Format code
make format
```

## Development

### Make Commands

```bash
make help          # Show available commands
make install       # Install dependencies
make run           # Start development server
make lint          # Run linter
make format        # Format code
make typecheck     # Run type checker
make docker-up     # Start with Docker Compose
make docker-down   # Stop containers
make clean         # Remove cache files
```

### Adding New Tools

1. Create a new tool file in `src/tools/`
2. Implement the tool interface from `src/tools/base.py`
3. Register the tool in `src/tools/toolkit.py`
4. Add the tool name to `TOOL_ALLOWLIST` in `.env`

Example:
```python
# src/tools/my_tool.py
from src.tools.base import Tool, ToolContext
from pydantic import BaseModel

class MyToolInput(BaseModel):
    query: str

class MyToolOutput(BaseModel):
    result: str

class MyTool:
    name = "my_tool.execute"
    input_model = MyToolInput
    output_model = MyToolOutput

    async def __call__(self, args: BaseModel, ctx: ToolContext) -> BaseModel:
        # Implementation here
        return MyToolOutput(result="...")

tool = MyTool()
```

## Deployment

### Docker

```bash
# Build image
docker build -t whatsapp-assistant .

# Run container
docker run -p 8000:8000 --env-file .env whatsapp-assistant
```

### Docker Compose (Recommended)

```bash
# Start all services (app + redis)
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

### Production Considerations

1. **Environment Variables**
   - Use secrets management (AWS Secrets Manager, Google Secret Manager)
   - Never commit `.env` to version control

2. **Scaling**
   - Use managed Redis (AWS ElastiCache, Google Cloud Memorystore)
   - Deploy multiple app instances behind a load balancer
   - Consider async workers for heavy processing

3. **Monitoring**
   - Enable LangSmith tracing
   - Set up error tracking (Sentry, Datadog)
   - Monitor Redis memory usage
   - Track WhatsApp webhook latency

4. **Security**
   - Enable HTTPS (required for Twilio webhooks)
   - Tighten CORS policy (remove `allow_origins=["*"]`)
   - Implement proper authentication for REST endpoints
   - Regularly rotate API keys

## Troubleshooting

### WhatsApp messages not being received

1. Check Twilio webhook URL is correct and publicly accessible
2. Verify webhook signature validation is working
3. Check Redis is running and accessible
4. Review application logs for errors

```bash
# Test webhook is accessible
curl https://your-domain.com/webhooks/whatsapp

# Check Redis connection
redis-cli ping
```

### Weather tool not working

1. Verify Google Weather API key is set
2. Check geocoding API is enabled in Google Cloud Console
3. Review rate limits on Google Cloud Console

### Rate limiting issues

Adjust limits in `.env`:
```bash
RATE_LIMIT_CHAT_PER_MIN=60  # Increase chat limit
RATE_LIMIT_TOOL_PER_MIN=30   # Increase tool limit
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT

## Support

For issues and questions:
- Open an issue on GitHub
- Check Twilio documentation: https://www.twilio.com/docs/whatsapp
- Review LangGraph docs: https://langchain-ai.github.io/langgraph/

## Acknowledgments

- Built with [LangGraph](https://github.com/langchain-ai/langgraph)
- WhatsApp integration via [Twilio](https://www.twilio.com/)
- Weather data from [Google Weather API](https://developers.google.com/maps/documentation/weather)
- Powered by [OpenAI](https://openai.com/)
