# Chef Big Max

Chef Big Max is an AI cooking assistant that helps a user choose and cook a dish from the ingredients they already have.

The project is built as an AI agent, not a fixed automation. It collects context, remembers the conversation, adapts to the user's skill level and restrictions, suggests dish options, and then generates a full recipe for the selected dish.

## Features

- Step-by-step user profiling
- Personalized dish suggestions from available ingredients
- Recipe generation for the selected dish
- Follow-up chat for substitutions, faster versions, scaling, and troubleshooting
- Streaming AI responses, so text appears in real time
- Chat history stored in SQLite
- Recipe cards with generated food images
- Fridge photo analysis — upload a photo of your fridge and the agent identifies ingredients and suggests dishes
- Simple web UI built with Flask templates, CSS, and JavaScript

## Agent Flow

1. **User profiling** — The agent asks for cooking skill level, allergies or restrictions, available tools, and time.
2. **Dish options** — After the profile is complete, the user gives ingredients or uploads a fridge photo. The agent suggests 3 to 5 possible dishes instead of immediately generating one recipe.
3. **Recipe generation** — The user selects one dish card. The agent creates a full recipe adapted to the user's profile.
4. **Follow-up** — The user can ask for substitutions, faster versions, scaling, or cooking help.

## Why This Is An AI Agent

This project is not a fixed sequence of steps. The assistant:

- adapts based on the user's answers;
- remembers previous messages in the session;
- chooses when to profile, suggest options, or generate a recipe;
- produces dynamic personalized output;
- guides the user through a cooking task instead of only returning one static answer.

## Tech Stack

- Python
- Flask
- Flask-SQLAlchemy
- SQLite
- JavaScript
- OpenRouter API
- Pexels API for recipe photos
- Server-Sent Events for streaming responses

## Setup

Install dependencies:

```
pip install -r requirements.txt
```

Create a `.env` file near the project files and add your API keys:

```
OPENROUTER_API_KEY=your_openrouter_api_key_here
PEXELS_API_KEY=your_pexels_api_key_here
SECRET_KEY=dev-secret-123
```

The Pexels key is used to search stable real food photos for recipe cards. You can get a free key from the Pexels API documentation: https://www.pexels.com/api/documentation/

Run the app:

```
python run.py
```

Open the app in your browser:

```
http://localhost:5000
```

## Demo Scenario

Use this flow during the defense:

1. Skill level: `home cook`
2. Dietary restrictions: `no allergies`
3. Tools: `full kitchen`
4. Time: `1 hour`
5. Ingredients: `potatoes, cheese, eggs, onion, butter`

The agent should suggest several dish options. Choose one card, then show how it generates the full recipe.

## Project Structure

```
app/
  models/
    recipe.py
    user.py
  routes/
    main.py
  services/
    ai_service.py
  static/
    script.js
    style.css
  templates/
    index.html
config.py
requirements.txt
run.py
```

## Notes And Limitations

- Recipe card images use Pexels search first. If Pexels is not configured or does not return a result, the app falls back to generated images.
- The AI response includes a hidden JSON block used by the app to update stages, profile data, and dish cards.
- Users can upload a photo of their fridge or ingredients, and the agent will analyze the image and suggest dishes based on what it sees.
  
