"""
Training data: DDL, documentation, and 25 question/SQL example pairs
for the Chinook sample database.
"""
from __future__ import annotations

CHINOOK_DDL = """
CREATE TABLE Artist (
    ArtistId INTEGER PRIMARY KEY,
    Name NVARCHAR(120)
);

CREATE TABLE Album (
    AlbumId INTEGER PRIMARY KEY,
    Title NVARCHAR(160) NOT NULL,
    ArtistId INTEGER NOT NULL REFERENCES Artist(ArtistId)
);

CREATE TABLE MediaType (
    MediaTypeId INTEGER PRIMARY KEY,
    Name NVARCHAR(120)
);

CREATE TABLE Genre (
    GenreId INTEGER PRIMARY KEY,
    Name NVARCHAR(120)
);

CREATE TABLE Track (
    TrackId INTEGER PRIMARY KEY,
    Name NVARCHAR(200) NOT NULL,
    AlbumId INTEGER REFERENCES Album(AlbumId),
    MediaTypeId INTEGER NOT NULL REFERENCES MediaType(MediaTypeId),
    GenreId INTEGER REFERENCES Genre(GenreId),
    Composer NVARCHAR(220),
    Milliseconds INTEGER NOT NULL,
    Bytes INTEGER,
    UnitPrice NUMERIC(10,2) NOT NULL
);

CREATE TABLE Playlist (
    PlaylistId INTEGER PRIMARY KEY,
    Name NVARCHAR(120)
);

CREATE TABLE PlaylistTrack (
    PlaylistId INTEGER NOT NULL REFERENCES Playlist(PlaylistId),
    TrackId INTEGER NOT NULL REFERENCES Track(TrackId),
    PRIMARY KEY (PlaylistId, TrackId)
);

CREATE TABLE Employee (
    EmployeeId INTEGER PRIMARY KEY,
    LastName NVARCHAR(20) NOT NULL,
    FirstName NVARCHAR(20) NOT NULL,
    Title NVARCHAR(30),
    ReportsTo INTEGER REFERENCES Employee(EmployeeId),
    BirthDate DATETIME,
    HireDate DATETIME,
    Address NVARCHAR(70),
    City NVARCHAR(40),
    State NVARCHAR(40),
    Country NVARCHAR(40),
    PostalCode NVARCHAR(10),
    Phone NVARCHAR(24),
    Fax NVARCHAR(24),
    Email NVARCHAR(60)
);

CREATE TABLE Customer (
    CustomerId INTEGER PRIMARY KEY,
    FirstName NVARCHAR(40) NOT NULL,
    LastName NVARCHAR(20) NOT NULL,
    Company NVARCHAR(80),
    Address NVARCHAR(70),
    City NVARCHAR(40),
    State NVARCHAR(40),
    Country NVARCHAR(40),
    PostalCode NVARCHAR(10),
    Phone NVARCHAR(24),
    Fax NVARCHAR(24),
    Email NVARCHAR(60) NOT NULL,
    SupportRepId INTEGER REFERENCES Employee(EmployeeId)
);

CREATE TABLE Invoice (
    InvoiceId INTEGER PRIMARY KEY,
    CustomerId INTEGER NOT NULL REFERENCES Customer(CustomerId),
    InvoiceDate DATETIME NOT NULL,
    BillingAddress NVARCHAR(70),
    BillingCity NVARCHAR(40),
    BillingState NVARCHAR(40),
    BillingCountry NVARCHAR(40),
    BillingPostalCode NVARCHAR(10),
    Total NUMERIC(10,2) NOT NULL
);

CREATE TABLE InvoiceLine (
    InvoiceLineId INTEGER PRIMARY KEY,
    InvoiceId INTEGER NOT NULL REFERENCES Invoice(InvoiceId),
    TrackId INTEGER NOT NULL REFERENCES Track(TrackId),
    UnitPrice NUMERIC(10,2) NOT NULL,
    Quantity INTEGER NOT NULL
);
"""

CHINOOK_DOCUMENTATION = """
## Chinook Database — Business Domain Reference

The Chinook database models a digital music store.

**Entities:**
- **Artist**: Music artists/bands with unique ArtistId.
- **Album**: Albums linked to one Artist. An artist may have many albums.
- **Track**: Individual songs. Each belongs to an Album, Genre, and MediaType.
  - `Milliseconds`: track duration.
  - `UnitPrice`: purchase price (typically $0.99 or $1.99).
- **Genre**: Music genre (Rock, Jazz, Classical, etc.).
- **MediaType**: File format (MPEG, AAC, Protected AAC, etc.).
- **Playlist**: Named playlists containing many tracks (M:M via PlaylistTrack).
- **Customer**: Store customers, each assigned a support representative (Employee).
- **Employee**: Staff members; `ReportsTo` is a self-referencing foreign key for org hierarchy.
- **Invoice**: Purchase records per customer. `Total` = sum of InvoiceLines.
- **InvoiceLine**: Individual line items linking Invoice → Track with price & quantity.

**Key business metrics:**
- Revenue = SUM(InvoiceLine.UnitPrice * InvoiceLine.Quantity)
- Top customers = customers with highest Invoice.Total sum
- Popular tracks = tracks appearing most in InvoiceLines
"""

EXAMPLE_QA_PAIRS: list[tuple[str, str]] = [
    (
        "How many tracks are there in total?",
        "SELECT COUNT(*) AS total_tracks FROM Track",
    ),
    (
        "List the top 10 best-selling tracks by revenue.",
        """SELECT t.Name AS track, ar.Name AS artist, 
       SUM(il.UnitPrice * il.Quantity) AS revenue
FROM InvoiceLine il
JOIN Track t ON t.TrackId = il.TrackId
JOIN Album al ON al.AlbumId = t.AlbumId
JOIN Artist ar ON ar.ArtistId = al.ArtistId
GROUP BY t.TrackId
ORDER BY revenue DESC
LIMIT 10""",
    ),
    (
        "Which artists have the most albums?",
        """SELECT ar.Name AS artist, COUNT(al.AlbumId) AS album_count
FROM Artist ar
JOIN Album al ON al.ArtistId = ar.ArtistId
GROUP BY ar.ArtistId
ORDER BY album_count DESC
LIMIT 10""",
    ),
    (
        "What are the top 5 countries by total revenue?",
        """SELECT c.Country, SUM(i.Total) AS total_revenue
FROM Invoice i
JOIN Customer c ON c.CustomerId = i.CustomerId
GROUP BY c.Country
ORDER BY total_revenue DESC
LIMIT 5""",
    ),
    (
        "How many customers are there per country?",
        """SELECT Country, COUNT(*) AS customer_count
FROM Customer
GROUP BY Country
ORDER BY customer_count DESC""",
    ),
    (
        "What is the average invoice total?",
        "SELECT AVG(Total) AS avg_invoice_total FROM Invoice",
    ),
    (
        "List all genres and the number of tracks in each.",
        """SELECT g.Name AS genre, COUNT(t.TrackId) AS track_count
FROM Genre g
LEFT JOIN Track t ON t.GenreId = g.GenreId
GROUP BY g.GenreId
ORDER BY track_count DESC""",
    ),
    (
        "Who are the top 5 customers by total spending?",
        """SELECT c.FirstName || ' ' || c.LastName AS customer,
       SUM(i.Total) AS total_spent
FROM Customer c
JOIN Invoice i ON i.CustomerId = c.CustomerId
GROUP BY c.CustomerId
ORDER BY total_spent DESC
LIMIT 5""",
    ),
    (
        "Show monthly revenue for 2013.",
        """SELECT strftime('%Y-%m', InvoiceDate) AS month,
       SUM(Total) AS revenue
FROM Invoice
WHERE strftime('%Y', InvoiceDate) = '2013'
GROUP BY month
ORDER BY month""",
    ),
    (
        "Which employee supports the most customers?",
        """SELECT e.FirstName || ' ' || e.LastName AS employee,
       COUNT(c.CustomerId) AS customer_count
FROM Employee e
JOIN Customer c ON c.SupportRepId = e.EmployeeId
GROUP BY e.EmployeeId
ORDER BY customer_count DESC
LIMIT 1""",
    ),
    (
        "What are the longest tracks?",
        """SELECT Name, Milliseconds / 60000 AS duration_minutes
FROM Track
ORDER BY Milliseconds DESC
LIMIT 10""",
    ),
    (
        "List all albums by 'Led Zeppelin'.",
        """SELECT al.Title AS album
FROM Album al
JOIN Artist ar ON ar.ArtistId = al.ArtistId
WHERE ar.Name = 'Led Zeppelin'""",
    ),
    (
        "What is the total revenue per media type?",
        """SELECT mt.Name AS media_type,
       SUM(il.UnitPrice * il.Quantity) AS revenue
FROM InvoiceLine il
JOIN Track t ON t.TrackId = il.TrackId
JOIN MediaType mt ON mt.MediaTypeId = t.MediaTypeId
GROUP BY mt.MediaTypeId
ORDER BY revenue DESC""",
    ),
    (
        "How many tracks does each playlist contain?",
        """SELECT p.Name AS playlist, COUNT(pt.TrackId) AS track_count
FROM Playlist p
LEFT JOIN PlaylistTrack pt ON pt.PlaylistId = p.PlaylistId
GROUP BY p.PlaylistId
ORDER BY track_count DESC""",
    ),
    (
        "Find customers who have never made a purchase.",
        """SELECT c.FirstName || ' ' || c.LastName AS customer, c.Email
FROM Customer c
LEFT JOIN Invoice i ON i.CustomerId = c.CustomerId
WHERE i.InvoiceId IS NULL""",
    ),
    (
        "Which city generates the most revenue?",
        """SELECT BillingCity AS city, SUM(Total) AS revenue
FROM Invoice
GROUP BY BillingCity
ORDER BY revenue DESC
LIMIT 5""",
    ),
    (
        "Show the org chart (who reports to whom).",
        """SELECT e.FirstName || ' ' || e.LastName AS employee,
       m.FirstName || ' ' || m.LastName AS manager
FROM Employee e
LEFT JOIN Employee m ON m.EmployeeId = e.ReportsTo
ORDER BY manager""",
    ),
    (
        "What percentage of tracks are Rock genre?",
        """SELECT ROUND(100.0 * SUM(CASE WHEN g.Name = 'Rock' THEN 1 ELSE 0 END)
                         / COUNT(*), 2) AS rock_percentage
FROM Track t
JOIN Genre g ON g.GenreId = t.GenreId""",
    ),
    (
        "List composers with more than 10 tracks.",
        """SELECT Composer, COUNT(*) AS track_count
FROM Track
WHERE Composer IS NOT NULL
GROUP BY Composer
HAVING track_count > 10
ORDER BY track_count DESC""",
    ),
    (
        "What is the average number of tracks per album?",
        """SELECT ROUND(AVG(track_count), 2) AS avg_tracks_per_album
FROM (
  SELECT AlbumId, COUNT(*) AS track_count
  FROM Track
  GROUP BY AlbumId
)""",
    ),
    (
        "Show total revenue by year.",
        """SELECT strftime('%Y', InvoiceDate) AS year, SUM(Total) AS revenue
FROM Invoice
GROUP BY year
ORDER BY year""",
    ),
    (
        "Which tracks have never been purchased?",
        """SELECT t.Name AS track, ar.Name AS artist
FROM Track t
JOIN Album al ON al.AlbumId = t.AlbumId
JOIN Artist ar ON ar.ArtistId = al.ArtistId
LEFT JOIN InvoiceLine il ON il.TrackId = t.TrackId
WHERE il.InvoiceLineId IS NULL
ORDER BY ar.Name""",
    ),
    (
        "Find all customers from Brazil.",
        """SELECT FirstName || ' ' || LastName AS customer, Email, City
FROM Customer
WHERE Country = 'Brazil'
ORDER BY LastName""",
    ),
    (
        "What is the most expensive track?",
        """SELECT Name, UnitPrice
FROM Track
ORDER BY UnitPrice DESC
LIMIT 1""",
    ),
    (
        "How many invoices were placed each month in 2012?",
        """SELECT strftime('%Y-%m', InvoiceDate) AS month, COUNT(*) AS invoice_count
FROM Invoice
WHERE strftime('%Y', InvoiceDate) = '2012'
GROUP BY month
ORDER BY month""",
    ),
]
