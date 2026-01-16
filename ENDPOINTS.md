# Lista Endpointów - Backend Delegacje

## Autentykacja (Auth)

### POST `/api/auth/register`
**Opis:** Rejestracja nowego użytkownika
**Request Body:**
```json
{
  "username": "string",
  "email": "string",
  "password": "string"
}
```
**Response:**
- 201: `{"status": "success", "user_id": int, "message": "User created"}`
- 400: `{"status": "error", "message": "Validation error"}`
- 409: `{"status": "error", "message": "User already exists"}`

### POST `/api/auth/login`
**Opis:** Logowanie użytkownika, zwraca JWT token
**Request Body:**
```json
{
  "email": "string",
  "password": "string"
}
```
**Response:**
- 200: `{"status": "success", "token": "jwt_token", "user_id": int, "user": {...}}`
- 401: `{"status": "error", "message": "Invalid credentials"}`
- 403: `{"status": "error", "message": "User account is inactive"}`

### GET `/api/auth/me`
**Opis:** Pobranie danych aktualnego zalogowanego użytkownika
**Headers:** `Authorization: Bearer <token>`
**Response:**
- 200: `{"status": "success", "user": {...}}`
- 401: `{"status": "error", "message": "Token is missing"}`

### GET `/api/auth/verify`
**Opis:** Weryfikacja JWT tokena
**Headers:** `Authorization: Bearer <token>`
**Response:**
- 200: `{"status": "success", "user_id": int, "valid": true}`
- 401: `{"status": "error", "message": "Invalid or expired token"}`

### POST `/api/auth/logout`
**Opis:** Wylogowanie użytkownika (opcjonalne - jeśli używamy refresh tokenów)
**Headers:** `Authorization: Bearer <token>`
**Response:**
- 200: `{"status": "success", "message": "Logged out successfully"}`

## Delegacje (Delegations)

### GET `/api/delegations`
**Opis:** Pobranie listy delegacji zalogowanego użytkownika
**Headers:** `Authorization: Bearer <token>`
**Response:**
- 200: `[{"id": int, "start_date": "date", "end_date": "date", "status": "string", ...}]`

### POST `/api/delegations`
**Opis:** Utworzenie nowej delegacji
**Headers:** `Authorization: Bearer <token>`
**Request Body:**
```json
{
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "country": "string (optional)",
  "city": "string (optional)",
  "name": "string (optional)",
  "purpose": "string (optional)",
  "status": "string (optional, default: 'draft')"
}
```
**Response:**
- 201: `{"id": int, "start_date": "date", "end_date": "date", "status": "string", "country": "string", "city": "string", "name": "string", "purpose": "string"}`

### GET `/api/delegations/<id>`
**Opis:** Pobranie szczegółów delegacji
**Headers:** `Authorization: Bearer <token>`
**Response:**
- 200: `{"id": int, "start_date": "date", "end_date": "date", "status": "string", "expenses": [...]}`
- 404: `{"status": "error", "message": "Delegation not found"}`

### PUT `/api/delegations/<id>`
**Opis:** Aktualizacja delegacji
**Headers:** `Authorization: Bearer <token>`
**Request Body:**
```json
{
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "country": "string",
  "city": "string",
  "name": "string",
  "purpose": "string",
  "status": "string"
}
```
**Response:**
- 200: `{"id": int, "start_date": "date", "end_date": "date", "status": "string", "country": "string", "city": "string", "name": "string", "purpose": "string"}`

### DELETE `/api/delegations/<id>`
**Opis:** Usunięcie delegacji
**Headers:** `Authorization: Bearer <token>`
**Response:**
- 200: `{"status": "success", "message": "Delegation deleted"}`

## Wydatki (Expenses)

### GET `/api/delegations/<delegation_id>/expenses`
**Opis:** Pobranie listy wydatków dla delegacji
**Headers:** `Authorization: Bearer <token>`
**Response:**
- 200: `[{"id": int, "amount": decimal, "pln_amount": decimal, ...}]`

### POST `/api/delegations/<delegation_id>/expenses`
**Opis:** Dodanie wydatku do delegacji
**Headers:** `Authorization: Bearer <token>`
**Request Body:**
```json
{
  "explanation": "string",
  "payed_at": "YYYY-MM-DD",
  "amount": decimal,
  "currency_id": int,
  "category_id": int
}
```
**Response:**
- 201: `{"id": int, "amount": decimal, "pln_amount": decimal, ...}`

## Użytkownicy (Users) - Opcjonalne

### GET `/api/users/<id>`
**Opis:** Pobranie danych użytkownika
**Headers:** `Authorization: Bearer <token>`
**Response:**
- 200: `{"id": int, "username": "string", "email": "string", ...}`

### PUT `/api/users/<id>`
**Opis:** Aktualizacja danych użytkownika
**Headers:** `Authorization: Bearer <token>`
**Response:**
- 200: `{"status": "success", "user": {...}}`
