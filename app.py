from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import sqlalchemy

app = Flask(__name__)
CORS(app)

# db connection here
YOUR_POSTGRES_PASSWORD = "postgres"
connection_string = f"postgresql://postgres:{YOUR_POSTGRES_PASSWORD}@localhost/postgres"
engine = sqlalchemy.create_engine(
    "postgresql://postgres:postgres@localhost/postgres"
)

db = engine.connect()

# function to wrap sql query result into proper format
def wrap_result(result):
    rows = []
    columns = list(result.keys())
    for row_number, row in enumerate(result):
        rows.append({})
        for column_number, value in enumerate(row):
            rows[row_number][columns[column_number]] = value
    return rows

@app.post("/api/customer/login")
def login_customer():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    try:
        # parameterised query to prevent sql injection
        query = sqlalchemy.text("SELECT * FROM users WHERE email=:email AND password=:password")
        result = db.execute(query, {"email":email, "password":password} ).fetchone()
        # if user found, retrieve customer details
        if result:
            query = f"SELECT * FROM customers WHERE user_id={result[0]}"
            res = db.execute(sqlalchemy.text(query)).fetchone()
            response = {
                "success": True,
                "customer": {
                    "customer_id": res[0],
                    "name": res[2],
                    "contact": res[3],
                }
            }
            return jsonify(response), 200
        else:
            response = {
                "success": False,
                "message": "Invalid email or password"
            }
            return jsonify(response), 401
    except Exception as e:
        db.rollback()
        return Response(str(e), 403)
    
@app.post("/api/owner/login")
def login_owner():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    try:
        query = sqlalchemy.text("SELECT * FROM users WHERE email=:email AND password=:password")
        result = db.execute(query, {"email":email, "password":password} ).fetchone()

        if result:
            query = f"SELECT * FROM owners WHERE user_id={result[0]}"
            res = db.execute(sqlalchemy.text(query)).fetchone()
            response = {
                "success": True,
                "owner": {
                    "owner_id": res[0],
                    "name": res[2],
                    "contact": res[3],
                }
            }
            return jsonify(response), 200
        else:
            response = {
                "success": False,
                "message": "Invalid email or password"
            }
            return jsonify(response), 401    
    except Exception as e:
        db.rollback()
        return Response(str(e), 403)
    
@app.post("/api/customer/create")
def create_customer():
    data = request.get_json()

    name = data.get("name")
    contact = data.get("contact")
    email = data.get("email")
    password = data.get("password")
    try:
        # Check if user with given email or contact already exists
        query = sqlalchemy.text("SELECT customer_id FROM customers "
                                "WHERE (email=:e OR contact=:c)")
        result = db.execute(query, {"e":email, "c":contact}).fetchone()
        if result:
            response = {
                "message": "User with given email or contact already exists"
            }
            return jsonify(response), 409

        # Insert new user into database
        query = f"SELECT MAX(user_id) from users"
        user_id = int(db.execute(sqlalchemy.text(query)).fetchone()[0] or 0) + 1
        query = f"SELECT MAX(customer_id) from customers"
        customer_id = int(db.execute(sqlalchemy.text(query)).fetchone()[0] or 0) + 1
        query = sqlalchemy.text(
            "INSERT INTO users (user_id, email, password) "
            "VALUES (:u, :e, :p)"
            )
        db.execute(query, {"u":user_id, "e":email, "p":password})
        db.commit()
        query = sqlalchemy.text(
            "INSERT INTO customers (customer_id, user_id, name, contact, email) "
            "VALUES (:cu, :u, :n, :c, :e)"
            )
        db.execute(query, {"cu":customer_id, "u":user_id, "n":name, "c":contact, "e":email})
        db.commit()
        return Response(query.text)
    except Exception as e:
        db.rollback()
        return Response(str(e), 403)

@app.post("/api/owner/create")
def create_owner():
    data = request.get_json()

    name = data.get("name")
    contact = data.get("contact")
    email = data.get("email")
    password = data.get("password")
    try:
        # Check if user with given email already exists
        query = sqlalchemy.text("SELECT owner_id FROM owners "
                                "WHERE (email=:e OR contact=:c)")
        result = db.execute(query, {"e":email, "c":contact}).fetchone()
        if result:
            response = {
                "message": "User with given email or contact already exists"
            }
            return jsonify(response), 409

        # Insert new user into database
        query = f"SELECT MAX(user_id) from users"
        user_id = int(db.execute(sqlalchemy.text(query)).fetchone()[0] or 0) + 1
        query = f"SELECT MAX(owner_id) from owners"
        owner_id = int(db.execute(sqlalchemy.text(query)).fetchone()[0] or 0) + 1
        query = sqlalchemy.text(
            "INSERT INTO users (user_id, email, password) "
            "VALUES (:u, :e, :p)"
            )
        db.execute(query, {"u":user_id, "e":email, "p":password})
        db.commit()
        query = sqlalchemy.text(
            "INSERT INTO owners (owner_id, user_id, name, contact, email) "
            "VALUES (:o, :u, :n, :c, :e)"
            )
        db.execute(query, {"o":owner_id, "u":user_id, "n":name, "c":contact, "e":email})
        db.commit()
        return Response(query.text)
    except Exception as e:
        db.rollback()
        return Response(str(e), 403)

@app.post('/api/cars')
def search_cars():
    data = request.get_json()
    pickupLocation = data.get('pickupLocation')
    seatCapacity = data.get('seatCapacity')
    try:
        query = sqlalchemy.text(
            "SELECT car_id, make_model, seat_capacity, pickup_location, rental_rate "
            "FROM cars "
            "WHERE " 
                "available = true "
                "AND ( "
                    "(:pickup_location = '' AND :seat_capacity = 0) OR "
                    "(:pickup_location = '' AND seat_capacity = :seat_capacity) OR "
                    "(pickup_location = :pickup_location AND :seat_capacity = 0) OR "
                    "(pickup_location = :pickup_location AND seat_capacity = :seat_capacity) "
                ")"
            )
        result = db.execute(query, {"pickup_location":pickupLocation, "seat_capacity":seatCapacity})
        result = wrap_result(result)
        return jsonify(result)
    except Exception as e:
        db.rollback()
        return Response(str(e), 403)

@app.post('/api/postcar')
def post_cars():
    data = request.get_json()
    owner_id = data.get('owner_id')
    makeModel = data.get('makeModel')
    pickupLocation = data.get('pickupLocation')
    seatCapacity = data.get('seatCapacity')
    rentalRate = data.get('rentalRate')
    try:
        # add new car to database
        query = f"SELECT MAX(car_id) from cars"
        car_id = int(db.execute(sqlalchemy.text(query)).fetchone()[0] or 0) + 1
        query = sqlalchemy.text("INSERT INTO cars VALUES (:c, :o, :m, :s, :p, :r, true)")
        db.execute(query, {"c":car_id, "o":owner_id, "m":makeModel, 
                           "s":seatCapacity, "p":pickupLocation, "r":rentalRate })
        db.commit()
        return Response(query.text)
    except Exception as e:
        db.rollback()
        return Response(str(e), 403)
    
@app.post('/api/getcars') 
def get_cars():
    owner_id = request.get_json()
    try:
        # retrieve cars of owner
        query = sqlalchemy.text(
            "SELECT car_id, make_model, seat_capacity, pickup_location, rental_rate, available "
            "FROM cars "
            "WHERE owner_id =:o")
        result = db.execute(query, {"o": owner_id})
        result = wrap_result(result)
        return jsonify(result)
    except Exception as e:
        db.rollback()
        return Response(str(e), 403)
    
@app.post('/api/rentcar')
def rent_cars():
    data = request.get_json()
    customer_id = data.get('customer_id')
    car_id = data.get('car_id')
    rental_days = data.get('rentalDays')
    rental_cost = data.get('rentalCost')
    pickup_location = data.get("pickup_location")
    try:
        # insert the rental record into the database
        query = f"SELECT MAX(rental_id) from rental"
        rental_id = int(db.execute(sqlalchemy.text(query)).fetchone()[0] or 0) + 1
        #status is pending by default
        query = sqlalchemy.text(
            "INSERT INTO rental (rental_id, customer_id, car_id, rental_days, total_cost, pickup_location) "
            "VALUES (:r, :cu, :c, :rd, :rc, :p)")
        db.execute(query, {"r":rental_id, "cu":customer_id, "c":car_id, 
                           "rd":rental_days, "rc":rental_cost, "p":pickup_location})
        db.commit()
        # update car availability to false
        query = sqlalchemy.text("UPDATE cars "
                                "SET available=false "
                                "WHERE car_id=:c")
        db.execute(query, {"c": car_id})
        db.commit()
        return Response(query.text)
    except Exception as e:
        db.rollback()
        return Response(str(e), 403)

@app.post('/api/getorders')
def get_orders():
    data = request.get_json()
    user_type = data.get('user_type')
    user_id = data.get('user_id')
    status = data.get('status')
    try:
        if user_type == 'customer':
            # retrieve rental records for the given customer
            query = sqlalchemy.text(
                "SELECT r.rental_id, c.make_model, r.pickup_location, r.rental_days, r.total_cost, o.contact, r.status "
                "FROM rental r, cars c, owners o "
                "WHERE c.car_id = r.car_id "
                "AND c.owner_id = o.owner_id "
                "AND r.customer_id = :c "
                "AND r.status = :s")
            result = db.execute(query, {"c":user_id, "s":status})
            
        else:
            # retrieve rental records for the given owner
            query = sqlalchemy.text(
                "SELECT r.rental_id, c.make_model, r.pickup_location, r.rental_days, r.total_cost, cu.contact, r.status "
                "FROM rental r, cars c, customers cu "
                "WHERE c.car_id = r.car_id "
                "AND r.customer_id = cu.customer_id "
                "AND c.owner_id = :o "
                "AND r.status = :s")
            result = db.execute(query, {"o":user_id, "s":status})
        result = wrap_result(result)
        return jsonify(result)
    except Exception as e:
        db.rollback()
        return Response(str(e), 403)
    
@app.post('/api/updateorder')
def update_order():
    data = request.get_json()
    rental_id = data.get('rental_id')
    status = data.get('status')
    try:
        # update status of rental
        query = sqlalchemy.text("UPDATE rental "
                                "SET status=:s "
                                "WHERE rental_id=:r")
        db.execute(query, {"r":rental_id, "s":status})
        db.commit()
        # update availability of car to true if cancelled or completed
        query = sqlalchemy.text(
            "UPDATE cars "
            "SET available=true "
            "WHERE car_id IN (SELECT car_id "
                            "FROM rental "
                            "WHERE rental_id=:r "
                            "AND status IN ('cancelled', 'completed'))")
        db.execute(query, {"r":rental_id})
        db.commit()
        return Response(query.text)
    except Exception as e:
        print(e)
        db.rollback()
        return Response(str(e), 403)    
    
@app.post('/api/getstats')
def get_stats():
    try:
        query = sqlalchemy.text("SELECT (SELECT COUNT(customer_id) FROM customers) total_customers, "
                                "(SELECT COUNT(owner_id) FROM owners) total_owners, "
                                "(SELECT COUNT(car_id) FROM cars) total_cars, "
                                "SUM(CASE status WHEN 'pending' THEN 1 ELSE 0 END) total_pending, "
                                "SUM(CASE status WHEN 'confirmed' THEN 1 ELSE 0 END) total_ongoing, "
                                "SUM(CASE status WHEN 'cancelled' THEN 1 ELSE 0 END) total_cancelled, "
                                "SUM(CASE status WHEN 'completed' THEN 1 ELSE 0 END) total_completed "
                                "FROM rental")
        result = db.execute(query)
        result = wrap_result(result)
        return jsonify(result)
    except Exception as e:
        db.rollback()
        return Response(str(e), 403)

@app.post('/api/getusers')
def get_users():
    data = request.get_json()
    user_type = data.get("user_type")
    id = str(data.get("id"))
    try:
        if user_type == 'customer':
            # list of customers
            query = sqlalchemy.text("SELECT c.customer_id id, c.name, c.contact, c.email, "
                                    "SUM(CASE status WHEN 'cancelled' THEN 1 ELSE 0 END) total_cancelled, "
                                    "SUM(CASE status WHEN 'completed' THEN 1 ELSE 0 END) total_completed "
                                    "FROM rental r "
                                    "RIGHT JOIN customers c "
                                    "ON r.customer_id = c.customer_id "
                                    "GROUP BY c.customer_id, c.name, c.contact, c.email "
                                    "ORDER BY id")
        else: 
            # list of owners
            query = sqlalchemy.text("SELECT o.owner_id id, o.name, o.contact, o.email, "
                                    "SUM(CASE status WHEN 'cancelled' THEN 1 ELSE 0 END) total_cancelled, "
                                    "SUM(CASE status WHEN 'completed' THEN 1 ELSE 0 END) total_completed, "
                                    "SUM(CASE status WHEN 'completed' THEN rental_rate ELSE 0 END) total_earnings, "
                                    "COUNT(DISTINCT c.car_id) total_cars "
                                    "FROM owners o "
                                    "LEFT JOIN cars c ON o.owner_id = c.owner_id "
                                    "LEFT JOIN rental r ON c.car_id = r.car_id "
                                    "WHERE (:id='' OR o.owner_id::text = :id)"
                                    "GROUP BY o.owner_id, o.name, o.contact, o.email "
                                    "ORDER BY id")
        result = db.execute(query, {"id":id})
        result = wrap_result(result)
        return jsonify(result)
    except Exception as e:
        db.rollback()
        return Response(str(e), 403)
    
@app.post('/api/deleteuser')
def delete_user():
    data = request.get_json()
    user_type = data.get('user_type')
    id = data.get('id') 
    try:
        if user_type == 'customer':
            # release cars booked by customers
            query = sqlalchemy.text("UPDATE cars "
                                    "SET available=true "
                                    "WHERE car_id IN "
                                    "(SELECT r.car_id "
                                    "FROM cars c, rental r, customers cc "
                                    "WHERE r.car_id = c.car_id "
                                    "AND r.customer_id = cc.customer_id "
                                    "AND (r.status = 'pending' or r.status = 'confirmed') "
                                    "AND cc.customer_id = :x)")
            db.execute(query, {"x": id})
            db.commit()
            query = sqlalchemy.text("DELETE FROM users "
                                    "WHERE user_id IN (SELECT user_id FROM customers "
				                                        "WHERE customer_id = :x)")
        else:
            query = sqlalchemy.text("DELETE FROM users "
                                    "WHERE user_id IN (SELECT user_id FROM owners "
				                                        "WHERE owner_id = :x)")
        db.execute(query, {"x": id})
        db.commit()
        return Response(query.text)
    except Exception as e:
        db.rollback()
        return Response(str(e), 403)

@app.post('/api/listcars')
def list_cars():
    try:
        query = sqlalchemy.text(
            "SELECT c.car_id, c.make_model, c.seat_capacity, c.pickup_location, c.rental_rate, "
            "SUM(CASE status WHEN 'completed' THEN 1 ELSE 0 END) total_rental "
            "FROM cars c "
            "LEFT JOIN rental r "
            "ON r.car_id = c.car_id "
            "GROUP BY c.car_id, c.make_model, c.seat_capacity, c.pickup_location, c.rental_rate"
            )
        result = db.execute(query)
        result = wrap_result(result)
        return jsonify(result)                       
    except Exception as e:
        db.rollback()
        return Response(str(e), 403)
    
@app.post('/api/deletecar')
def delete_car():
    car_id = request.get_json()
    try:
        query = sqlalchemy.text("DELETE FROM cars "
                                "WHERE car_id=:c")
        db.execute(query, {"c":car_id})
        db.commit()
        return Response(query.text)                       
    except Exception as e:
        db.rollback()
        return Response(str(e), 403)
    
@app.post('/api/updateuser')
def update_user():
    data = request.get_json()
    id = data.get("id")
    contact = data.get("newContact")
    name = data.get("newName")
    user_type = data.get("user_type")
    
    try:
        if user_type == "customer":
            query = sqlalchemy.text("UPDATE customers "
                                    "SET name =:n, contact =:c "
                                    "WHERE customer_id =:i")
        else:
            query = sqlalchemy.text("UPDATE owners "
                                    "SET name =:n, contact =:c "
                                    "WHERE owner_id =:i")
        db.execute(query, {"n":name, "c":contact, "i":id})
        db.commit()
        return Response(query.text)
    except Exception as e:
        db.rollback()
        return Response(str(e), 403)    

@app.post('/api/adminlogin')
def admin_login():
    data = request.get_json()
    username =  data.get("username")
    password = data.get("password")
    try:
        query = sqlalchemy.text("SELECT * FROM admin "
                                "WHERE username=:u AND password=:p")
        result = db.execute(query, {"u":username, "p":password}).fetchone()
        if result:
            return jsonify({"success":True}), 200
        else:
            return jsonify({"success":False}), 401 
    except Exception as e:
        print(e)
        db.rollback()
        return Response(str(e), 403) 
    
@app.post('/api/updatecar')
def update_car():
    data = request.get_json()
    car_id = data.get("car_id")
    rental_rate = data.get("rentalRateEdit")
    pickup_location = data.get("pickupLocationEdit")
    try:
        query = sqlalchemy.text("UPDATE cars "
                                "SET rental_rate=:r, pickup_location=:p "
                                "WHERE car_id=:c")
        db.execute(query, {"r": rental_rate, "p":pickup_location, "c": car_id})
        db.commit()
        return Response(query.text)
    except Exception as e:
        db.rollback()
        return Response(str(e), 403)    

# This method can be used by the waitress-serve CLI 
def create_app():
   return app

# The port where the debuggable DB management API is served
PORT = 2222

# Running the Flask app on the localhost/0.0.0.0, port 2223
if __name__ == "__main__":
    app.run("0.0.0.0", PORT)

    # Alternatively, you can use Waitress to run the application instead of Flask's development server
    # You can do this by uncommenting the following lines and commenting out the previous line:
    # from waitress import serve
    # serve(app, host="0.0.0.0", port=PORT)