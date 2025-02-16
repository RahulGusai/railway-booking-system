
  <h1>Railway Ticket Reservation API</h1>
  <p>
    This repository contains a Railway Ticket Reservation API built with <strong>FastAPI</strong> and <strong>SQLAlchemy</strong>.
    It implements a comprehensive railway ticket booking system with features including seat allocation (Confirmed, RAC, Waiting List),
    soft deletion, and promotion logic after cancellations. The application is containerized with Docker and prepopulates the seat mapping data.
  </p>

  <h2>Table of Contents</h2>
  <ul>
    <li><a href="#overview">Overview</a></li>
    <li><a href="#features">Features</a></li>
    <li><a href="#data-models">Data Models</a></li>
    <li><a href="#api-endpoints">API Endpoints</a></li>
    <li><a href="#concurrency--locking">Concurrency &amp; Locking</a></li>
    <li><a href="#installation--running-the-application">Installation &amp; Running the Application</a></li>
    <li><a href="#notes">Notes</a></li>
  </ul>

  <h2 id="overview">Overview</h2>
  <p>
    The Railway Ticket Reservation API allows users to book railway tickets with multiple passengers.
    It allocates seats according to available capacity with priority rules (e.g., lower berth priority for seniors or for adult females with children)
    and supports a cancellation flow that promotes RAC entries to confirmed and waiting list entries to RAC.
  </p>

  <h2 id="features">Features</h2>
  <ul>
    <li><strong>Ticket Booking:</strong> Create a ticket with multiple passengers. Automatic seat allocation based on Confirmed (max 63), RAC (max 9), and Waiting List (max 10) capacities. Priority allocation for lower berths is given to passengers aged 60 or above and to adult females with children.</li>
    <li><strong>Ticket Cancellation &amp; Promotion:</strong> Soft-deletes a ticket along with its associated passengers and berth allocations using a <code>deleted_at</code> timestamp. After cancellation, promotion logic reassigns seats (RAC to confirmed, waiting list to RAC) if capacity allows.</li>
    <li><strong>Containerized Deployment:</strong> The project is Dockerized for easy setup and deployment.</li>
    <li><strong>Database Migrations:</strong> Alembic is used for managing schema changes.</li>
  </ul>

  <h2 id="data-models">Data Models</h2>
  <h3>Ticket</h3>
  <ul>
    <li><strong>Table:</strong> <code>tickets</code></li>
    <li><strong>Fields:</strong>
      <ul>
        <li><code>id</code>: Primary key</li>
        <li><code>source</code>: (Optional) Starting station</li>
        <li><code>destination</code>: (Optional) Ending station</li>
        <li><code>status</code>: Ticket status (<code>upcoming</code>, <code>ongoing</code>, <code>cancelled</code>, <code>completed</code>)</li>
        <li><code>booking_user_id</code>: User ID of the person who booked the ticket</li>
        <li><code>deleted_at</code>: Timestamp for soft deletion</li>
        <li><code>pnr</code>: A 10-digit unique number (automatically generated)</li>
      </ul>
    </li>
    <li><strong>Relationships:</strong> One ticket has many passengers.</li>
  </ul>

  <h3>Passenger</h3>
  <ul>
    <li><strong>Table:</strong> <code>passengers</code></li>
    <li><strong>Fields:</strong>
      <ul>
        <li><code>id</code>: Primary key</li>
        <li><code>name</code>: Passenger name</li>
        <li><code>gender</code>: Passenger gender</li>
        <li><code>age</code>: Passenger age</li>
        <li><code>ticket_id</code>: Foreign key to the associated ticket</li>
        <li><code>deleted_at</code>: Timestamp for soft deletion</li>
      </ul>
    </li>
    <li><strong>Relationships:</strong> Belongs to a ticket; one-to-one with berth allocation.</li>
  </ul>

  <h3>BerthAllocation</h3>
  <ul>
    <li><strong>Table:</strong> <code>berth_allocation</code></li>
    <li><strong>Fields:</strong>
      <ul>
        <li><code>id</code>: Primary key</li>
        <li><code>status</code>: Allocation status (<code>CNF</code> for confirmed, <code>RAC</code> for RAC, <code>WL</code> for waiting list)</li>
        <li><code>seat_mapping_id</code>: Foreign key referencing the static seat mapping (if a physical seat is allocated)</li>
        <li><code>passenger_id</code>: Foreign key linking to the passenger</li>
        <li><code>deleted_at</code>: Timestamp for soft deletion</li>
      </ul>
    </li>
    <li><strong>Relationships:</strong> Belongs to a passenger; references a seat mapping entry.</li>
  </ul>

  <h3>SeatMapping</h3>
  <ul>
    <li><strong>Table:</strong> <code>seat_mapping</code></li>
    <li><strong>Fields:</strong>
      <ul>
        <li><code>id</code>: Primary key</li>
        <li><code>seat_number</code>: Unique seat number</li>
        <li><code>berth_type</code>: Type of berth (e.g., lower, middle, upper, side-upper, side-lower)</li>
        <li><code>category</code>: Either <code>confirmed</code> or <code>rac</code></li>
      </ul>
    </li>
    <li><strong>Usage:</strong> This static table maps seat numbers to berth types, aiding in seat allocation.</li>
  </ul>

  <h2 id="api-endpoints">API Endpoints</h2>
  <h3>POST <code>/api/v1/tickets/book</code></h3>
  <p>
    <strong>Description:</strong> Creates a new ticket with one or more passengers. The API applies seat allocation logic based on availability and priority (e.g., lower berth for seniors or adult females with children) and wraps the entire process in a transaction with row-level locking.
  </p>
  <pre>
{
  "booking_user_id": 1,
  "source": "Station A",
  "destination": "Station B",
  "passengers": [
    { "name": "raj", "gender": "male", "age": 45 },
    { "name": "sara", "gender": "female", "age": 32 },
    { "name": "mark", "gender": "male", "age": 38 },
    { "name": "david", "gender": "male", "age": 33 },
    { "name": "eva", "gender": "female", "age": 26 }
  ]
}
    </pre>
    <p>
      <strong>Response:</strong> Returns the created ticket with an auto-generated PNR and allocation details.
    </p>

  <h3>POST <code>/api/v1/tickets/cancel/{ticket_id}</code></h3>
  <p>
    <strong>Description:</strong> Soft-deletes a ticket (and its associated passengers and berth allocations) by setting the <code>deleted_at</code> timestamp. After cancellation, promotion logic is executed to promote RAC entries to confirmed seats and waiting list entries to RAC if available.
  </p>
  <p><strong>Response:</strong> A message confirming cancellation and promotions.</p>

  <h3>GET <code>/api/v1/tickets/booked</code></h3>
  <p>
    <strong>Description:</strong> Retrieves a list of all booked (non-deleted) tickets along with associated passenger and allocation details.
  </p>

  <h3>GET <code>/api/v1/tickets/available</code></h3>
  <p>
    <strong>Description:</strong> Returns the counts of available seats in Confirmed, RAC, and Waiting List categories.
  </p>
  <pre>
{
  "available_confirmed": 12,
  "available_rac": 3,
  "available_waiting": 10
}
    </pre>

<h2 id="concurrency--locking">Concurrency &amp; Locking</h2>
<p>
  The API uses row-level locking via <code>with_for_update()</code> in the <code>find_available_seat</code> function to lock the selected seat rows during a booking transaction. This ensures that while a booking is in progress, the selected seats are not available to other concurrent transactions. The entire booking process is executed within a single transaction; locks are released once the transaction is committed.
</p>

<h2 id="installation--running-the-application">Installation &amp; Running the Application</h2>
<h3>Local Development</h3>
<ol>
  <li>Clone the repository:
    <pre>git clone &lt;repository-url&gt;
cd railway-reservation</pre>
      </li>
      <li>Install dependencies:
        <pre>pip install -r requirements.txt</pre>
      </li>
      <li>Run the application:
        <pre>uvicorn app.main:app --host 0.0.0.0 --port 8000</pre>
      </li>
      <li>Access the API docs at: <a href="http://0.0.0.0:8000/docs">http://0.0.0.0:8000/docs</a></li>
    </ol>

  <h3>Docker</h3>
  <ol>
    <li>Build the Docker image:
      <pre>docker build -t railway-reservation:latest .</pre>
    </li>
    <li>Run the container:
      <pre>docker run -p 8000:8000 railway-reservation:latest</pre>
    </li>
    <li>Alternatively, use Docker Compose:
      <pre>docker-compose up --build</pre>
    </li>
  </ol>

<h2 id="notes">Notes</h2>
<ul>
   <li><strong>Soft Deletion:</strong> Tickets, passengers, and berth allocations are not hard-deleted; a <code>deleted_at</code> timestamp is set instead.</li>
    <li><strong>Prioritization:</strong> Lower berth booking is prioritized for senior citizens (age ≥ 60) and for adult females with children.</li>
    <li><strong>Concurrency:</strong> A locking mechanism is applied during booking transactions to prevent multiple users from accessing seats that are being booked concurrently.</li>
    <li><strong>Testing:</strong> Use the Swagger UI at <code>/docs</code> or Postman to test API endpoints.</li>
</ul>

<p>
  For further details, please refer to the source code and comments within the repository.
</p>

<p>Happy Coding!</p>

    
