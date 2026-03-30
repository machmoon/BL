# BentleyLibrary API Documentation

## URL Patterns

### Home
- **URL**: `/`
- **View**: `index`
- **Method**: GET
- **Description**: Home page

### Search
- **URL**: `/search/`
- **View**: `search_results`
- **Method**: GET
- **Parameters**:
  - `q`: Search query (optional)
  - `published_date_start`: Start date filter (optional)
  - `published_date_end`: End date filter (optional)
  - `available_quantity`: Quantity filter (optional)
  - `title`, `author`, `publisher`, `isbn`: Field-specific filters (optional)

### Book Details
- **URL**: `/book/<int:book_id>/`
- **View**: `book_page`
- **Method**: GET
- **Description**: Display individual book page with borrowing information

### Checkout
- **URL**: `/checkout/<str:isbn>/`
- **View**: `checkout`
- **Method**: GET, POST
- **POST Parameters**:
  - `first_name`: Borrower's first name (required)
  - `last_name`: Borrower's last name (required)
  - `email`: Borrower's email (required, must be valid email)
- **Response**: Redirects to index on success, error page on failure

### Checkin
- **URL**: `/checkin/`
- **View**: `checkin`
- **Method**: GET, POST
- **POST Parameters**:
  - `isbn`: ISBN of book to check in (required)
- **Response**: Redirects to index on success, error page on failure

### Advanced Search
- **Primary URL**: `/advanced-search/`
- **Legacy URL**: `/advanced_search_results/`
- **View**: `AdvancedSearchResults` (Class-based view)
- **Method**: GET
- **Parameters**:
  - `search_type`: 'everything' or 'catalog'
  - `field[]`: Array of field names to search
  - `operator[]`: Array of operators (`icontains`, `exact`, etc.)
  - `search_term[]`: Array of search terms
  - `logical_operator[]`: Array of logical operators (AND, OR, NOT)
  - `published_date_start`: Start date filter
  - `published_date_end`: End date filter

### Resource
- **Primary URL**: `/resources/`
- **Legacy URL**: `/resource.html`
- **View**: `resource_view`
- **Method**: GET
- **Description**: Resource page

## Error Responses

User-facing validation and workflow errors are rendered back into the page with a `200` response and an error message. The notable non-200 case is:

- **404**: Missing book detail page

## Success Messages

- Checkout: "Thanks for checking out the book."
- Checkin: "Book checked in successfully."

## Example Requests

### Checkout a Book
```http
POST /checkout/1234567890123/
Content-Type: application/x-www-form-urlencoded

first_name=John&last_name=Doe&email=john@example.com
```

### Search for Books
```http
GET /search/?q=Python&published_date_start=2020-01-01
```

### Checkin a Book
```http
POST /checkin/
Content-Type: application/x-www-form-urlencoded

isbn=1234567890123
```



