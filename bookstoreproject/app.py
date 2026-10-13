from flask import Flask, jsonify, request
from flask import render_template
from database import get_connection

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/books")
def get_books():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM BOOK")
    books = cursor.fetchall()

    cursor.close()
    connection.close()

    return jsonify(books)
@app.route('/customers')
def get_customers():
    connection= get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM CUSTOMER")
    customers = cursor.fetchall()

    cursor.close()
    connection.close()

    return jsonify(customers)
@app.route('/orders')
def get_orders():
    connection= get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM BOOK_ORDER")
    orders = cursor.fetchall()

    cursor.close()
    connection.close()

    return jsonify(orders)
@app.route('/returns')
def get_returns():
    connection= get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM BOOK_RETURN")
    returns = cursor.fetchall()

    cursor.close()
    connection.close()

    return jsonify(returns)
@app.route('/publishers')
def get_publishers():
    connection= get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM PUBLISHER")
    publishers = cursor.fetchall()

    cursor.close()
    connection.close()

    return jsonify(publishers)
@app.route('/fine')
def get_fines():
    connection=get_connection()
    cursor=connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM FINE")
    fine=cursor.fetchall()

    cursor.close()
    connection.close()
    return jsonify(fine)
@app.route("/authors")
def get_authors():
    connection=get_connection()
    cursor=connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM AUTHOR")
    authors=cursor.fetchall()

    cursor.close()
    connection.close()
    return jsonify(authors)
@app.route('/book/<int:book_id>')
def get_book(book_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM BOOK WHERE book_id = %s",
        (book_id,)
    )

    book = cursor.fetchone()

    cursor.close()
    connection.close()

    if book:
        return jsonify(book)

    return jsonify({"message": "Book not found"}), 404
@app.route('/search_books')
def search_books():
    title = request.args.get('title', '')

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM BOOK WHERE title LIKE %s",
        ('%' + title + '%',)
    )

    books = cursor.fetchall()

    cursor.close()
    connection.close()

    return jsonify(books)

@app.route('/add_book', methods=['POST'])
def add_book():
    data = request.get_json()

    connection = get_connection()
    cursor = connection.cursor()

    query = """
        INSERT INTO BOOK
        (isbn, title, edition, pub_year, price, total_copies,
         available_copies, publisher_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    values = (
        data['isbn'],
        data['title'],
        data['edition'],
        data['pub_year'],
        data['price'],
        data['total_copies'],
        data['available_copies'],
        data['publisher_id']
    )

    cursor.execute(query, values)
    connection.commit()

    cursor.close()
    connection.close()

    return jsonify({"message": "Book added successfully"}), 201
@app.route('/update_price/<int:book_id>', methods=['PUT'])
def update_price(book_id):
    data = request.get_json()
    new_price = data['price']

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "UPDATE BOOK SET price = %s WHERE book_id = %s",
        (new_price, book_id)
    )

    connection.commit()

    if cursor.rowcount == 0:
        cursor.close()
        connection.close()
        return jsonify({"message": "Book not found"}), 404

    cursor.close()
    connection.close()

    return jsonify({"message": "Book price updated successfully"})

@app.route('/delete_book/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM BOOK WHERE book_id = %s",
        (book_id,)
    )

    connection.commit()

    if cursor.rowcount == 0:
        cursor.close()
        connection.close()
        return jsonify({"message": "Book not found"}), 404

    cursor.close()
    connection.close()

    return jsonify({"message": "Book deleted successfully"})
@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.get_json()

    customer_id = data['customer_id']
    book_id = data['book_id']

    connection = get_connection()
    cursor = connection.cursor()

    try:
        connection.start_transaction()

        # Check book availability and lock its row
        cursor.execute(
            "SELECT available_copies FROM BOOK WHERE book_id = %s FOR UPDATE",
            (book_id,)
        )
        book = cursor.fetchone()

        if book is None:
            connection.rollback()
            return jsonify({"message": "Book not found"}), 404

        if book[0] <= 0:
            connection.rollback()
            return jsonify({"message": "Book is out of stock"}), 400

        # Create the order
        cursor.execute(
            """
            INSERT INTO BOOK_ORDER
            (order_date, due_date, customer_id, book_id)
            VALUES (CURDATE(), DATE_ADD(CURDATE(), INTERVAL 7 DAY), %s, %s)
            """,
            (customer_id, book_id)
        )

        # Reduce available copies
        cursor.execute(
            """
            UPDATE BOOK
            SET available_copies = available_copies - 1
            WHERE book_id = %s
            """,
            (book_id,)
        )

        connection.commit()

        return jsonify({
            "message": "Order placed successfully",
            "order_id": cursor.lastrowid
        }), 201

    except Exception:
        connection.rollback()
        app.logger.exception("Failed to place order")
        return jsonify({"message": "Unable to place order"}), 500

    finally:
        cursor.close()
        connection.close()
@app.route('/return_book', methods=['POST'])
def return_book():
    data = request.get_json()

    order_id = data['order_id']
    book_condition = data.get('book_condition', 'Good')

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        # Get order and book details
        cursor.execute("""
            SELECT bo.book_id, bo.due_date, b.price
            FROM BOOK_ORDER bo
            JOIN BOOK b ON bo.book_id = b.book_id
            WHERE bo.order_id = %s
            FOR UPDATE
        """, (order_id,))

        order = cursor.fetchone()

        if order is None:
            connection.rollback()
            return jsonify({"message": "Order not found"}), 404

        # Prevent duplicate returns
        cursor.execute("""
            SELECT return_id
            FROM BOOK_RETURN
            WHERE order_id = %s
        """, (order_id,))

        if cursor.fetchone():
            connection.rollback()
            return jsonify({
                "message": "This book has already been returned"
            }), 400

        # Record the return
        cursor.execute("""
            INSERT INTO BOOK_RETURN
            (return_date, book_condition, order_id)
            VALUES (CURDATE(), %s, %s)
        """, (book_condition, order_id))

        return_id = cursor.lastrowid

        # Update available stock
        cursor.execute("""
            UPDATE BOOK
            SET available_copies = available_copies + 1
            WHERE book_id = %s
        """, (order['book_id'],))

        # Calculate overdue days
        cursor.execute("""
            SELECT GREATEST(
                DATEDIFF(CURDATE(), due_date), 0
            ) AS late_days
            FROM BOOK_ORDER
            WHERE order_id = %s
        """, (order_id,))

        late_days = cursor.fetchone()['late_days']
        fines_created = []

        # Late fine: Rs. 5 per overdue day
        if late_days > 0:
            late_fine = late_days * 5

            cursor.execute("""
                INSERT INTO FINE
                (fine_type, amount, paid_status, paid_date, return_id)
                VALUES (%s, %s, %s, %s, %s)
            """, ('Late', late_fine, 'Unpaid', None, return_id))

            fines_created.append({
                "type": "Late",
                "amount": float(late_fine)
            })

        # Damaged-book fine: 50% of book price
        if book_condition.lower() == 'damaged':
            damaged_fine = float(order['price']) * 0.5

            cursor.execute("""
                INSERT INTO FINE
                (fine_type, amount, paid_status, paid_date, return_id)
                VALUES (%s, %s, %s, %s, %s)
            """, ('Damaged', damaged_fine, 'Unpaid', None, return_id))

            fines_created.append({
                "type": "Damaged",
                "amount": damaged_fine
            })

        connection.commit()

        return jsonify({
            "message": "Book returned successfully",
            "return_id": return_id,
            "late_days": late_days,
            "fines": fines_created
        }), 201

    except Exception:
        connection.rollback()
        app.logger.exception("Book return failed")
        return jsonify({
            "message": "Unable to process return. Check the VS Code terminal."
        }), 500

    finally:
        cursor.close()
        connection.close()
if __name__ == "__main__":
    app.run(debug=True)