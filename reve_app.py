from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from bson.json_util import dumps
from bson.objectid import ObjectId
import json
from datetime import datetime,  timedelta
import random
from bson.binary import Binary  # Import Binary for storing bytes
import base64

import smtplib
import bcrypt

from pass_keys import email_passes


from flask_cors import *
app = Flask(__name__)

# MongoDB Configuration
app.config["MONGO_URI"] = "mongodb://localhost:27017/art"
mongo = PyMongo(app)

HOST = "smtp-mail.outlook.com"
PORT = 587

pass_keys = email_passes()
FROM_EMAIL = pass_keys['email']
PASSWORD = pass_keys['pass']
PASSCODE = pass_keys['passCode']
# print(FROM_EMAIL)
# print(PASSWORD)



def hash_password(password):
    # Generate a salt
    salt = bcrypt.gensalt()
    # Hash the password with the salt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password
# Home route


@app.route('/')
def home():
    return "Welcome to the Flask MongoDB API!"


@app.route('/userAuth', methods=['POST'])
@cross_origin()
def authenticate_user():
    data = request.json
    # print(data)
    if data:
        user = mongo.db.user.find_one({"email":data['email']})
        user = json.loads(dumps(user))
        if user:
            # Check if the provided password matches the stored hashed password
            # print(user)
            stored_hashed_password = user['password']
        
            if isinstance(stored_hashed_password, dict):
                # If retrieved as dict, convert to bytes
                stored_hashed_password = stored_hashed_password['$binary']['base64']
                stored_hashed_password = base64.b64decode(stored_hashed_password.encode('utf-8'))

            elif isinstance(stored_hashed_password, Binary):
                stored_hashed_password = bytes(stored_hashed_password)

            if bcrypt.checkpw(data['password'].encode('utf-8'), stored_hashed_password):
                print("Password is valid.")
                return jsonify(message="User Authenticated successfully"), 201
            else:
                print("Invalid password.")
                return jsonify(message="User Not Authenticated"), 400
        else:
            print("User not found.")
            return jsonify(message="User Not Found"), 400
        # if len(json.loads(dumps(user)))>0:
            
    else:
        return jsonify(message="User Not Authenticated"), 400
    

# Create a new document
@app.route('/add', methods=['POST'])
@cross_origin()
def add_document():
    data = request.json
    # print(data)
    if data:
        ids = [mongo.db.artWorks.insert_one({"image":image}).inserted_id for image in data['images']]
        data['images'] = ids
        data['image1'] = ids[0]
        data['image2'] = ids[1]
        data['image3'] = ids[2]
        data['image4'] = ids[3]
        data['image5'] = ids[4]
        data['created_on'] = datetime.now();
        data['updated_on'] = datetime.now();

        id = mongo.db.art.insert_one(data)
        print(id.inserted_id)
        return jsonify(message="Document added successfully"), 201
    else:
        return jsonify(message="No data provided"), 400



@app.route('/documents/<status>/<lastId>', methods=['GET'])
@cross_origin()
def get_documents(status = "inactive",lastId=""):
    limit = 10 if status == 'active' else 100
    if lastId != "none":
        filter = {'_id': {'$lt': ObjectId(lastId)}}
        if status == "active":
            filter  = {'_id': {'$lt': ObjectId(lastId)},'active':True}
    else:
        if status == "active":
            filter  = {'active':True}
        else:
            filter = {}

    documents = mongo.db.art.find(filter).sort("_id",-1).limit(limit)
    documents = json.loads(dumps(documents))


    hasMore = False
    if documents:
        if lastId != "none":
            countFilter = {'_id': {'$lt': ObjectId(documents[-1]['_id']["$oid"])}}
            if status == "active":
                countFilter = {'_id': {'$lt': ObjectId(documents[-1]['_id']["$oid"])},'active':True}
        else:
            if status == "active":
                countFilter = {'_id': {'$lt': ObjectId(documents[-1]['_id']["$oid"])},'active':True}
            else:
                countFilter = {'_id': {'$lt': ObjectId(documents[-1]['_id']["$oid"])}}
        # print(countFilter)
        hasMore = True if len(json.loads(dumps((mongo.db.art.find(countFilter))))) > 0 else False
    
    # print(hasMore)
    for document in documents:
        # print(document['image1'])
        document['image1'] = dumps(mongo.db.artWorks.find_one({'_id':ObjectId(document['image1']['$oid'])}))
        document['hasMore'] = hasMore
    return json.dumps(documents), 200  # Dumps to convert Cursor to JSON string


@app.route('/homeDocument/<imageSection>/<imageIndex>', methods=['GET'])
@cross_origin()
def get_home_document(imageSection , imageIndex):
    
    filter  = {'imageSection':imageSection,'imageIndex':int(imageIndex)}

    documents = mongo.db.homeImages.find(filter)
    documents = json.loads(dumps(documents))

    return json.dumps(documents), 200  

@app.route('/homeDocument/<imageSection>/<imageIndex>', methods=['POST'])
@cross_origin()
def update_home_document(imageSection,imageIndex):
    data = request.json
    # print(data)
    if data:
        if len(json.loads(dumps(mongo.db.homeImages.find({"imageSection":imageSection,"imageIndex":int(imageIndex)})))) > 0:
            mongo.db.homeImages.update_one({"imageSection":imageSection,"imageIndex":int(imageIndex)},{"$set":{"imageIndex":int(imageIndex),"imageSection":imageSection,"image":data['image'],"name":data['name'],"height":data['height'],"width":data['width'],"artworkUrl":data['artworkUrl']}})
        else:
            mongo.db.homeImages.insert_one({"imageIndex":int(imageIndex),"imageSection":imageSection,"image":data['image'],"name":data['name'],"height":data['height'],"width":data['width'],"artworkUrl":data['artworkUrl']})
        
        return jsonify(message="Document updated successfully"), 201
    else:
        return jsonify(message="No data provided"), 400


@app.route('/documentsSorted/<status>/<order>/<lastId>', methods=['GET'])
@cross_origin()
def get_documents_sorted(status = "inactive",order = "none",lastId="none"):
    # print("here in")
    limit = 10
    # order_1_condition = ['Asc','none','all','active','inactive']
    # order_not1_condition = ['Desc']
    order_num = -1 if order.endswith("Desc") else 1
    order_field = order.replace("Asc","").replace("Desc","")
    if order_field == "none" or order_field == 'all' or order_field == "active" or order_field == 'inactive':
        order_field = "_id"
    
    if status == "active":
        if lastId != "none":
            filter = {'_id': {'$lt': ObjectId(lastId)},'active':True}
        else:
            filter = {'active':True}
    else:
        if lastId != "none":
            filter = {'_id': {'$lt': ObjectId(lastId)}}
        else:
            filter = {}
    
        # if order == "none":
        #     documents = mongo.db.art.find({'active':True}).sort("_id",1)
        # if order == "nameAsc":
        #     documents = mongo.db.art.find({'active':True}).sort("name",1)
        # if order == "nameDesc":
        #     documents = mongo.db.art.find({'active':True}).sort("name",-1)
        # if order == "ratingAsc":
        #     documents = mongo.db.art.find({'active':True}).sort("rating",1)
        # if order == "ratingDesc":
        #     documents = mongo.db.art.find({'active':True}).sort("rating",-1)
        # if order == "ratingDesc":
        #     documents = mongo.db.art.find({'active':True}).sort("rating",-1)
        # if order == "all":
        #     documents = mongo.db.art.find().sort("_id",1)
        # if order == "active":
        #     documents = mongo.db.art.find({'active':True}).sort("_id",1)
        # if order == "inactive":
        #     documents = mongo.db.art.find({'active':False}).sort("_id",1)
    print(filter)
    documents = mongo.db.art.find(filter).sort(order_field,order_num).limit(limit)
    # else:
    #     documents = mongo.db.art.find()


    documents = json.loads(dumps(documents))

    hasMore = False
    if documents:
        if lastId != "none":
            countFilter = {'_id': {'$lt': ObjectId(documents[-1]['_id']["$oid"])}}
            if status == "active":
                countFilter = {'_id': {'$lt': ObjectId(documents[-1]['_id']["$oid"])},'active':True}
        else:
            if status == "active":
                countFilter = {'_id': {'$lt': ObjectId(documents[-1]['_id']["$oid"])},'active':True}
            else:
                countFilter = {'_id': {'$lt': ObjectId(documents[-1]['_id']["$oid"])}}
        # print(countFilter)
        hasMore = True if len(json.loads(dumps((mongo.db.art.find(countFilter))))) > 0 else False
    # print(hasMore)

    for document in documents:
        # print(document['image1'])
        document['image1'] = dumps(mongo.db.artWorks.find_one({'_id':ObjectId(document['image1']['$oid'])}))
        document['hasMore'] = hasMore

    return json.dumps(documents), 200  # Dumps to convert Cursor to JSON string

@app.route('/corouselDocuments', methods=['GET'])
@cross_origin()
def get_corousel_documents():
    # print("here in")
    documents = mongo.db.homeImages.find({"imageSection":"corousel"}).limit(5).sort( "imageIndex", 1 )
    documents = json.loads(dumps(documents))

    return json.dumps(documents), 200  # Dumps to convert Cursor to JSON string


@app.route('/corouselDocuments1', methods=['GET'])
@cross_origin()
def get_corousel_documents1():
    # print("here in")
    documents = mongo.db.homeImages.find({"imageSection":"corousel"}).limit(1).sort( "imageIndex", 1 )
    documents = json.loads(dumps(documents))

    return json.dumps(documents), 200  # Dumps to convert Cursor to JSON string

@app.route('/homeGridDocuments', methods=['GET'])
@cross_origin()
def get_home_Grid_documents():
    # print("here in")
    documents = mongo.db.homeImages.find({"imageSection":"homeGrid"}).limit(6).sort( "imageIndex", 1 )
    documents = json.loads(dumps(documents))
    # for document in documents:
    #     # print(document['image1'])
    #     document['image1'] = dumps(mongo.db.artWorks.find_one({'_id':ObjectId(document['image1']['$oid'])}))

    return json.dumps(documents), 200  # Dumps to convert Cursor to JSON string


@app.route('/capturArtMetrics/<sessionId>/<artId>', methods=['GET'])
@cross_origin()
def record_art_mertrics(sessionId,artId):
    current_time = datetime.now()
    # Calculate the time 60 seconds ago
    time_threshold = current_time - timedelta(seconds=60)

    # Query to find documents with the specified field value and timestamp within the last 60 seconds
    query = {
        "art": artId,  
        "timestamp": {"$gte": time_threshold}  
    }

    # Count the documents that match the query
    count = mongo.db.artworkAccessMetrics.count_documents(query)

    # Check if there are any duplicates
    if count > 0:
        # print(f"Found {count} duplicate document(s) with the field value '{id}' in the last 60 seconds.")
        # return True
        pass
    else:
        # print(f"No duplicates found with the field value '{id}' in the last 60 seconds.")
        # print("adding metrics")
        mongo.db.artworkAccessMetrics.insert_one({"art":artId,"sessionId":sessionId,"timestamp":datetime.now()})
        # return False
    return jsonify(message="metrics Captured"), 200

@app.route('/capturPageVisits/<user>/<sessionId>', methods=['GET'])
@cross_origin()
def record_home_page_visit_mertrics(user,sessionId):
    # print("user:",user)
    # print("sessionId",sessionId)
    # Query to find documents with the specified field value and timestamp within the last 60 seconds
    query = {
        "sessionId": sessionId
    }

    # Count the documents that match the query
    count = mongo.db.homePageVisitMetrics.count_documents(query)

    # Check if there are any duplicates
    if count > 0:
        pass
    else:
        mongo.db.homePageVisitMetrics.insert_one({"sessionId":sessionId,"user":user,"timestamp":datetime.now()})
        # return False
    return jsonify(message="home page visit metrics Captured"), 200

@app.route('/capturViewAllArtPageVisits/<user>/<sessionId>', methods=['GET'])
@cross_origin()
def record_artList_page_visit_mertrics(user,sessionId):
    # print("user:",user)
    # print("sessionId",sessionId)
    # Query to find documents with the specified field value and timestamp within the last 60 seconds
    query = {
        "sessionId": sessionId
    }

    # Count the documents that match the query
    count = mongo.db.artListPageVisitMetrics.count_documents(query)

    # Check if there are any duplicates
    if count > 0:
        pass
    else:
        mongo.db.artListPageVisitMetrics.insert_one({"sessionId":sessionId,"user":user,"timestamp":datetime.now()})
        # return False
    return jsonify(message="page visit metrics Captured"), 200
    

# Retrieve a document by ID
@app.route('/document/<id>', methods=['GET'])
@cross_origin()
def get_document(id):
    # print("documnet accessed by:", user)
    # if user == "user":
    #     print("in here")
    #     mongo.db.artworkAccessMetrics.insert_one({"image":id,"timestamp":datetime.now()})
    document = mongo.db.art.find_one({'_id': ObjectId(id)})
    if document:
        document = json.loads(dumps(document))
        document['image1'] = dumps(mongo.db.artWorks.find_one({'_id':ObjectId(document['image1']['$oid'])}))
        document['image2'] = dumps(mongo.db.artWorks.find_one({'_id':ObjectId(document['image2']['$oid'])}))
        document['image3'] = dumps(mongo.db.artWorks.find_one({'_id':ObjectId(document['image3']['$oid'])}))
        document['image4'] = dumps(mongo.db.artWorks.find_one({'_id':ObjectId(document['image4']['$oid'])}))
        document['image5'] = dumps(mongo.db.artWorks.find_one({'_id':ObjectId(document['image5']['$oid'])}))
        document['images'] = [json.loads(document['image'+str(index)])['image'] for index in range(1,6)]
        return dumps(document), 200
    else:
        return jsonify(message="Document not found"), 404
    
# Contact for purchase
@app.route('/contactForPurchase', methods=['POST'])
@cross_origin()
def contactForPurchase():
    data = request.json
    # print(data)
    if data:
        admin = mongo.db.user.find_one({'role': "admin"})
        if admin:
            # print(dumps(admin))
            admin_email = json.loads(dumps(admin))['email']
            # print(email)
            # print(json.loads(dumps(admin))["_id"]['$oid'])
        else:
            return jsonify(message="No Admin Found."), 404
        query = {
            "sessionId":data['sessionId'],
            "artName":data['artName'],
            "artId":data['artId'],
            "firstName":data['firstName'],
            "lastName":data['lastName'],
            "email":data['email']
        }
        data['timestamp']  = datetime.now()
        data['seen'] = False
        data['contacted'] = False
        # Count the documents that match the query
        count = mongo.db.contactForPurchaseLogs.count_documents(query)

        # Check if there are any duplicates
        if count > 0:
            pass
        else:
            mongo.db.contactForPurchaseLogs.insert_one(data)

        try:
            MESSAGE = f"""Subject: Enquiry for Artwork - {data["artName"]}.
            

            Hi Anwar,
            Myself {data["firstName"]} {data["lastName"]}, Reaching out to know more regarding the below artwork.
            Artwork Name: {data["artName"]},
            Artwork Id : {data["artId"]},
            Artwork Size : {data["artSize"]}

            Message: {data["comments"]}

            My Contact: {data["email"]}

            Thanks,
            """
        
            smtp = smtplib.SMTP(HOST, PORT)
            status_code, response =  smtp.ehlo()
            # print(f"[*] Echoing the server: {status_code} {response}")
            status_code, response =  smtp.starttls()
            # print(f"[*] Starting TLS connection: {status_code} - {response}")
            status_code, response = smtp.login(FROM_EMAIL, PASSWORD)
            # print(f"[*] Logging in: {status_code} {response}")
            smtp.sendmail(FROM_EMAIL, admin_email, MESSAGE) 
            smtp.quit()
            print("Email Sent!")
            return jsonify(message="Contacted Artist Successfully!"), 201
        except Exception as e:
            print(e)
            return jsonify(message="Unable to send email."), 400 
    else:
        return jsonify(message="No data provided"), 400
    
# Contact artist
@app.route('/contact', methods=['POST'])
@cross_origin()
def contact():
    data = request.json
    # print(data)
    if data:
        admin = mongo.db.user.find_one({'role': "admin"})
        if admin:
            # print(dumps(admin))
            admin_email = json.loads(dumps(admin))['email']
            # print(email)
            # print(json.loads(dumps(admin))["_id"]['$oid'])
        else:
            return jsonify(message="No Admin Found."), 404
        query = {
            "sessionId":data['sessionId'],
            "firstName":data['firstName'],
            "lastName":data['lastName'],
            "email":data['email'],
            
        }
        data['timestamp']  = datetime.now()
        data['seen'] = False
        data['contacted'] = False
        # Count the documents that match the query
        count = mongo.db.contactLogs.count_documents(query)

        # Check if there are any duplicates
        if count > 0:
            pass
        else:
            mongo.db.contactLogs.insert_one(data)

        try:
            MESSAGE = f"""Subject: Interested in Your Art

            Hi Anwar,
            Myself {data["firstName"]} {data["lastName"]}, Reaching out to know more regarding the your artwork.
                        
            Message: {data["comments"]}

            My Contact: {data["email"]}

            Thanks,
            """
        
            smtp = smtplib.SMTP(HOST, PORT)
            status_code, response =  smtp.ehlo()
            # print(f"[*] Echoing the server: {status_code} {response}")
            status_code, response =  smtp.starttls()
            # print(f"[*] Starting TLS connection: {status_code} - {response}")
            status_code, response = smtp.login(FROM_EMAIL, PASSWORD)
            # print(f"[*] Logging in: {status_code} {response}")
            smtp.sendmail(FROM_EMAIL, admin_email, MESSAGE) 
            smtp.quit()
            print("Email Sent!")
            return jsonify(message="Contacted Artist Successfully!"), 201
        except Exception as e:
            print(e)
            return jsonify(message="Unable to send email."), 400 
    else:
        return jsonify(message="No data provided"), 400
    
# Contact artist
@app.route('/forgotPassword', methods=['GET'])
@cross_origin()
def forgot_password():
    # print("here")
    # data = request.json
    # Generate a random 6-digit number
    verification_code = random.randint(100000, 999999)
    admin = mongo.db.user.find_one({'role': "admin"})
    if admin:
        # print(dumps(admin))
        email = json.loads(dumps(admin))['email']
        # print(email)
        # print(json.loads(dumps(admin))["_id"]['$oid'])
    else:
        return jsonify(message="No Admin Found."), 404

    result = mongo.db.user.update_one({'_id': ObjectId(json.loads(dumps(admin))["_id"]['$oid'])}, {"$set": {"verificationCode":verification_code}})
    if result.modified_count > 0:
            # print(data)
        # print("after update")
        try:
            MESSAGE = f"""Subject: Password Reset Request

            Hi Admin,
            Please User Below Verification Code for Password Reset.
            {verification_code}
            Thanks,
            """
        
            smtp = smtplib.SMTP(HOST, PORT)
            status_code, response =  smtp.ehlo()
            # print(f"[*] Echoing the server: {status_code} {response}")
            status_code, response =  smtp.starttls()
            # print(f"[*] Starting TLS connection: {status_code} - {response}")
            status_code, response = smtp.login(FROM_EMAIL, PASSWORD)
            # print(f"[*] Logging in: {status_code} {response}")
            smtp.sendmail(FROM_EMAIL, email, MESSAGE) 
            smtp.quit()
            print("Verification Code Email Sent!")
            return jsonify(message="Verification code sent Successfully!"), 201
        except Exception as e:
            print(e)
            return jsonify(message="Unable to send verification code."), 400 
    else:
        return jsonify(message="No changes made or document not found"), 404


# Update a document by ID
@app.route('/document/<id>', methods=['PUT'])
@cross_origin()
def update_document(id):
    data = request.json
    # print(data)
    existing_artwork = mongo.db.art.find_one({'_id': ObjectId(id)})
    existing_artwork = json.loads(dumps(existing_artwork))['images']
    for image in existing_artwork:
        # print(image['$oid'])
        delete_artwork_document(image['$oid'])
        
    if data:
        ids = [mongo.db.artWorks.insert_one({"image":image}).inserted_id for image in data['images']]
        data['images'] = ids
        data['image1'] = ids[0]
        data['image2'] = ids[1]
        data['image3'] = ids[2]
        data['image4'] = ids[3]
        data['image5'] = ids[4]
        data['updated_on'] = datetime.now();
        data['rating']  = float(data['rating'])
        # id = mongo.db.art.insert_one(data)
        result = mongo.db.art.update_one({'_id': ObjectId(id)}, {"$set": data})
        if result.modified_count > 0:
            return jsonify(message="Document updated successfully"), 200
        else:
            return jsonify(message="No changes made or document not found"), 404
        # pass
        # return jsonify(message="No data provided"), 400
    else:
        return jsonify(message="No data provided"), 400


@app.route('/updatePassword', methods=['PUT'])
@cross_origin()
def update_password():
    data = request.json
    # print(data)
    if data:
        # print("in here")
        # doc = mongo.db.user.find_one({'role':"admin",'verificationCode':int(data['verificationCode'])})
        # print(dumps(doc))
        result = mongo.db.user.update_one({'role': "admin",'verificationCode':int(data['verificationCode'])}, {"$set": {"password":hash_password(data['password']),"verificationCode":random.randint(100000, 999999)}})
        if result.modified_count > 0:
            return jsonify(message="Password updated successfully"), 200
        else:
            return jsonify(message="Password Update failed."), 405
    else:
        return jsonify(message="No data provided"), 400

# Helper function to convert ObjectId to string
def serialize_document(doc):
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            doc[key] = str(value)
    return doc

@app.route('/userVisitMetrics', methods=['GET'])
@cross_origin()
def get_user_visit_metrics():
    # Extract user_id from query parameters
    # user_id = request.args.get('user')
    user_id  = "user"
    if not user_id:
        return jsonify(message="User ID not provided"), 400

    # MongoDB connection setup
    # mongo_uri = 'mongodb://localhost:27017/'
    # client = MongoClient(mongo_uri)
    # db_name = 'art'
    # collection_name = 'artListPageVisitMetrics'
    # collection = client[db_name][collection_name]

    # Common match stage to filter by user
    # match_stage = { '$match': { 'user': user_id } }
    now = datetime.utcnow()
    start_of_month = datetime(now.year, now.month, 1)
    end_of_month = start_of_month + timedelta(days=32)
    end_of_month = end_of_month.replace(day=1)

    # Common match stage to filter by user
    match_stage = { '$match': { 'user': user_id } }

    # Aggregation pipeline for daily visits within the current month
    daily_pipeline = [
        match_stage,
        {
            '$match': {
                'timestamp': {
                    '$gte': start_of_month,
                    '$lt': end_of_month
                }
            }
        },
        {
            '$group': {
                '_id': {
                    'year': { '$year': "$timestamp" },
                    'month': { '$month': "$timestamp" },
                    'day': { '$dayOfMonth': "$timestamp" }
                },
                'visitCount': { '$sum': 1 }
            }
        },
        {
            '$sort': { "_id.year": 1, "_id.month": 1, "_id.day": 1 }
        }
    ]

    # Aggregation pipeline for monthly visits
    monthly_pipeline = [
        match_stage,
        {
            '$group': {
                '_id': {
                    'year': { '$year': "$timestamp" },
                    'month': { '$month': "$timestamp" }
                },
                'visitCount': { '$sum': 1 }
            }
        },
        {
            '$sort': { "_id.year": 1, "_id.month": 1 }
        }
    ]

    # Aggregation pipeline for quarterly visits
    quarterly_pipeline = [
        match_stage,
        {
            '$group': {
                '_id': {
                    'year': { '$year': "$timestamp" },
                    'quarter': {
                        '$cond': [
                            { '$lte': [{ '$month': "$timestamp" }, 3] }, 1,
                            {
                                '$cond': [
                                    { '$lte': [{ '$month': "$timestamp" }, 6] }, 2,
                                    {
                                        '$cond': [
                                            { '$lte': [{ '$month': "$timestamp" }, 9] }, 3,
                                            4
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                },
                'visitCount': { '$sum': 1 }
            }
        },
        {
            '$sort': { "_id.year": 1, "_id.quarter": 1 }
        }
    ]

    # Aggregation pipeline for yearly visits
    yearly_pipeline = [
        match_stage,
        {
            '$group': {
                '_id': { 'year': { '$year': "$timestamp" } },
                'visitCount': { '$sum': 1 }
            }
        },
        {
            '$sort': { "_id.year": 1 }
        }
    ]

    try:
        # Execute the aggregation pipelines
        daily_visits = list(mongo.db.artListPageVisitMetrics.aggregate(daily_pipeline))
        monthly_visits = list(mongo.db.artListPageVisitMetrics.aggregate(monthly_pipeline))
        quarterly_visits = list(mongo.db.artListPageVisitMetrics.aggregate(quarterly_pipeline))
        yearly_visits = list(mongo.db.artListPageVisitMetrics.aggregate(yearly_pipeline))

        # Format results into a structured dictionary
        result = {
            'daily': [{
                'date': f"{doc['_id']['year']}-{doc['_id']['month']:02d}-{doc['_id']['day']:02d}",
                'visitCount': doc['visitCount']
            } for doc in daily_visits],
            'monthly': [{
                'date': f"{doc['_id']['year']}-{doc['_id']['month']:02d}",
                'visitCount': doc['visitCount']
            } for doc in monthly_visits],
            'quarterly': [{
                'date': f"Q{doc['_id']['quarter']} {doc['_id']['year']}",
                'visitCount': doc['visitCount']
            } for doc in quarterly_visits],
            'yearly': [{
                'date': f"{doc['_id']['year']}",
                'visitCount': doc['visitCount']
            } for doc in yearly_visits]
        }

        # Aggregation pipeline for artwork views
        pipeline = [
            {
                '$addFields': {
                    'artObjectId': { '$toObjectId': '$art' }
                }
            },
            {
                '$lookup': {
                    'from': 'art',
                    'localField': 'artObjectId',
                    'foreignField': '_id',
                    'as': 'artworkDetails'
                }
            },
            {
                '$unwind': '$artworkDetails'
            },
            {
                '$group': {
                    '_id': '$artObjectId',
                    'artworkName': { '$first': '$artworkDetails.name' },
                    'accessCount': { '$sum': 1 }
                }
            },
            {
                '$sort': { 'accessCount': -1 }
            },
            {
                '$limit': 20
            },
            {
                '$project': {
                    '_id': 0,
                    'artworkId': '$_id',
                    'artworkName': 1,
                    'accessCount': 1
                }
            }
        ]

        # Execute the aggregation pipeline
        top_artworks = list(mongo.db.artworkAccessMetrics.aggregate(pipeline))
        serialized_artworks = [serialize_document(doc) for doc in top_artworks]
        result['top_artworks'] = serialized_artworks

        # Aggregation pipeline to get top artworks by contact count
        pipeline = [
            {
                '$group': {
                    '_id': '$artId',
                    'artworkName': { '$first': '$artName' },
                    'contactCount': { '$sum': 1 }
                }
            },
            {
                '$sort': { 'contactCount': -1 }
            },
            {
                '$limit': 20
            },
            {
                '$project': {
                    '_id': 0,
                    'artworkId': '$_id',
                    'artworkName': 1,
                    'contactCount': 1
                }
            }
        ]

        # Execute the aggregation pipeline
        top_contact_artworks = list(mongo.db.contactForPurchaseLogs.aggregate(pipeline))
        result['top_contact_artworks'] = top_contact_artworks

        return jsonify(result), 200

    except Exception as e:
        return jsonify(message=f"Error retrieving metrics: {str(e)}"), 500

@app.route('/deleteArtwork/<id>', methods=['GET'])
@cross_origin()
def delete_art(id):
    result = mongo.db.art.delete_one({'_id': ObjectId(id)})
    if result.deleted_count > 0:
        return jsonify(message="Document deleted successfully"), 200
    else:
        return jsonify(message="Document not found"), 404

@app.route('/getPurchaseEnquiries', methods=['POST'])
@cross_origin()
def get_purchase_enquiries():
    data = request.json
    # print(data)
    if data:
        pass_code = data['passCode']
        if pass_code == PASSCODE:

            enquiries = mongo.db.contactForPurchaseLogs.find().sort('timestamp',-1)
            enquiries = json.loads(dumps(enquiries))
            if enquiries:
                purchase_enquiries = []
                for enquiry in enquiries:
                    purchase_enquiries.append({"id": enquiry['_id']['$oid'],
                                               "name": enquiry['firstName'] + " " + enquiry['lastName'],
                                               "email": enquiry['email'],
                                               "artName": enquiry['artName'],
                                               "artSize": enquiry['artSize'],
                                               "comments": enquiry['comments'],
                                               "artId": enquiry['artId'],
                                               "date": convert_timestamp_to_ddmmyy(enquiry['timestamp']['$date']) if 'timestamp' in enquiry.keys() else "",
                                               "seen": True if 'seen' in enquiry.keys() and enquiry['seen'] == True else False,
                                               "contacted": True if 'contacted' in enquiry.keys() and enquiry['contacted'] == True else False})
                    
                return dumps(purchase_enquiries), 200
            else:
                print("No Purchase Enquiries found")
                return jsonify(message="No Purchase Enquiries found"), 400
        else:
            return jsonify(message="Invalid Passcode"), 400
        # if len(json.loads(dumps(user)))>0:
            
    else:
        return jsonify(message="Invalid Passcode"), 400
    
@app.route('/getContactEnquiries', methods=['POST'])
@cross_origin()
def get_contact_enquiries():
    data = request.json
    # print(data)
    if data:
        pass_code = data['passCode']
        if pass_code == PASSCODE:

            enquiries = mongo.db.contactLogs.find().sort('timestamp',-1)
            enquiries = json.loads(dumps(enquiries))
            if enquiries:
                purchase_enquiries = []
                for enquiry in enquiries:
                    purchase_enquiries.append({"id": enquiry['_id']['$oid'],
                                               "name": enquiry['firstName'] + " " + enquiry['lastName'],
                                               "email": enquiry['email'],
                                               "comments": enquiry['comments'],
                                               "date": convert_timestamp_to_ddmmyy(enquiry['timestamp']['$date']) if 'timestamp' in enquiry.keys() else "",
                                               "seen": True if 'seen' in enquiry.keys() and enquiry['seen'] == True else False,
                                               "contacted": True if 'contacted' in enquiry.keys() and enquiry['contacted'] == True else False})
                    
                return dumps(purchase_enquiries), 200
            else:
                print("No Contact Enquiries found")
                return jsonify(message="No Contact Enquiries found"), 400
        else:
            return jsonify(message="Invalid Passcode"), 400
        # if len(json.loads(dumps(user)))>0:
            
    else:
        return jsonify(message="Invalid Passcode"), 400
    
@app.route('/updateEnquiryStatus', methods=['POST'])
@cross_origin()
def update_enquiry_status():
    data = request.json
    print(data)
    if data:
        type = data['type']
        id = data['enquiryId']
        seen = data['seen']
        contacted = data['contacted']

        if type == 'purchase':
            try:
                mongo.db.contactForPurchaseLogs.update_one({"_id": ObjectId(id)}, {"$set": {"seen":seen, "contacted":contacted}})
                print("enquirty status updated successfully for purchase enquery " + id)
                return jsonify(message="enquirty status updated successfully for purchase enquery " + id), 200
            except Exception as e:
                print("Error updating enquiry status for purchase enquery " + id + " error : " + e)
                return jsonify(message="enquirty status cannot be updated for purchase enquery " + id), 400
        else:
            try:
                mongo.db.contactLogs.update_one({"_id": ObjectId(id)}, {"$set": {"seen":seen, "contacted":contacted}})
                print("enquirty status updated successfully for purchase enquery " + id)
                return jsonify(message="enquirty status updated successfully for purchase enquery " + id), 200
            except Exception as e:
                print("Error updating enquiry status for purchase enquery " + id + " error : " + e)
                return jsonify(message="enquirty status cannot be updated for purchase enquery " + id), 400
        
    else:
        return jsonify(message="cannot update enquiry status"), 400

def convert_timestamp_to_ddmmyy(timestamp_str):
  """
  Converts a timestamp string in the format "YYYY-MM-DDTHH:MM:SS.SSS" 
  to the "ddmmyy" format using the datetime module.

  Args:
    timestamp_str: The timestamp string to convert.

  Returns:
    The timestamp string in the "ddmmyy" format.
  """
  print(timestamp_str)
  try:
    # Parse the timestamp string into a datetime object
    timestamp_obj = datetime.fromisoformat(timestamp_str[:-1]) 

    # Extract day, month, and year components
    day = timestamp_obj.day
    month = timestamp_obj.month
    year = str(timestamp_obj.year)[-2:]  # Get the last two digits of the year

    # Format the timestamp in "ddmmyy" format
    ddmmyy_str = f"{day:02d}/{month:02d}/{year}" 
    return ddmmyy_str
  except ValueError as e:
    print(e)
    print(f"Invalid timestamp format: {timestamp_str}")
    return None
  
def delete_artwork_document(id):
    result = mongo.db.artWorks.delete_one({'_id': ObjectId(id)})
    if result.deleted_count > 0:
        return jsonify(message="Document deleted successfully"), 200
    else:
        return jsonify(message="Document not found"), 404

if __name__ == '__main__':
    app.run(debug=True,host="0.0.0.0",port=5001)
