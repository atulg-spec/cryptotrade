# TradeHub

TradeHub is a Django-based trading dashboard with real-time market updates, order execution, portfolio tracking, and wallet/payments workflows.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies.
3. Configure environment variables.
4. Run migrations.
5. Start the development server.

```bash
python -m venv env
env\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

## Environment Variables

The application now reads runtime settings from environment variables:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`

Use `.env.example` as the local template.

## Project Structure

The codebase is organized by domain apps, with shared service modules to keep request handlers thin and business logic reusable.

```
accounts/               # auth, user profile
assets/                 # trading orders, positions, watchlist
assets/services/        # trading service layer
dashboard/              # dashboard pages and context
payments/               # wallet transactions and payment flows
stockmanagement/        # market data + websocket consumers
tradehub/services/      # shared cross-app services (listing/pagination/time filters)
templates/              # Django templates and Tailwind-based partials
static/assets/js/       # frontend modules
```

## Architecture Notes

- Views/controllers: parse requests, validate inputs, format responses.
- Services: implement business workflows (`assets/services/trading_service.py`).
- Models: data persistence and state.
- Websockets: async consumers in `stockmanagement/consumers.py`.
- Shared listing logic: `tradehub/services/listing.py`.

## Frontend Conventions

- Tailwind utility classes are the styling baseline.
- Reusable UI partials live under `templates/dashboard/partials/`:
  - `ui-button.html`
  - `ui-card.html`
  - `ui-modal-shell.html`
  - `ui-table-shell.html`
  - `ui-chart-shell.html`
  - `ui-skeleton.html`

## Tests

Run the full test suite:

```bash
python manage.py test
```

Added baseline smoke coverage includes:
- order initiation flow
- orders page rendering
- transactions page rendering

## Extending Features

1. Add/extend business logic inside a service module first.
2. Keep view functions focused on HTTP boundaries.
3. Reuse shared listing/pagination helpers for list endpoints.
4. Build new UI with reusable Tailwind partials before page-specific markup.
5. Add or update tests for every user-visible behavior change.