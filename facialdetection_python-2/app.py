from flask import Flask, request, render_template
import boto3
import io
from PIL import Image
import base64

app = Flask(__name__)

rekognition = boto3.client('rekognition', region_name='us-east-1')
dynamodb = boto3.client('dynamodb', region_name='us-east-1')
s3 = boto3.client('s3')

@app.route("/health", methods=["GET"])
def health():
    return {"status":"success"}

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    if 'image' not in request.files:
        return "No file part"
    
    image = request.files['image']
    if image.filename == '':
        return "No selected file"

    image = Image.open(image)
    stream = io.BytesIO()
    image.save(stream, format="JPEG")
    image_binary = stream.getvalue()

    response = rekognition.search_faces_by_image(
        CollectionId="facialanalysiscomparision",
        Image={'Bytes': image_binary}
    )

    if not response['FaceMatches']:
        return "No record found"
    else:
        results = []
        for match in response['FaceMatches']:
            face_id = match['Face']['FaceId']
            confidence = match['Face']['Confidence']

            face = dynamodb.get_item(
                TableName='facialanalysiscomparision',
                Key={'RekognitionId': {'S': face_id}}
            )
            print(face)
            if 'Item' in face:
                full_name = face['Item']['FullName']['S']
                image_path = face['Item']['S3Path']['S']
                s3_bucket_name = image_path.split("/")[0]
                #s3_object_prefix = image_path.split("/")[1] + "/" + image_path.split("/")[2]
                s3_object_prefix = image_path.split("/")[1]
                image_object = s3.get_object(Bucket=s3_bucket_name, Key=s3_object_prefix)
                image_data = image_object['Body'].read()
                image_data_base64 = base64.b64encode(image_data).decode('utf-8')
            else:
                full_name = 'no match found in person lookup'

            results.append((face_id, confidence, full_name, image_data_base64))

        return render_template("results.html", results=results)

if __name__ == "__main__":
    app.run()