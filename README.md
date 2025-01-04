# ai-mystery-game
Mystery Game Serverless Application is designed to generate and manage image-based crossword puzzles using AI within a serverless architecture.

<p align="center">
  <img src="https://github.com/user-attachments/assets/77118c44-591e-4249-8de2-b84eacbe8876" alt="Mystery_1" />
</p>



## Features

- **AWS SAM**: Framework for building serverless applications.
- **Dynamic Image Generation**: Integrate with OpenAI's DALL-E and ChatGPT to generate images and mysteries on demand.
- **Event-Driven Processing**: Trigger Lambda functions based on API requests and DynamoDB streams.
- **Image Management**: Store and retrieve images from an S3 bucket.
- **API Endpoints**: Interact with Lambda functions via RESTful APIs.
- **Metadata Storage**: Use DynamoDB to store and manage image metadata.
- **Secure Configuration**: Manage sensitive information using AWS Systems Manager Parameter Store.


<p align="center">
  <img src="https://github.com/user-attachments/assets/5c9253a5-c823-455c-b1dd-a6e22fa60d1c" alt="Mystery" />
</p>



### Deployment Instructions

You can deploy the application using either the AWS SAM CLI or the AWS CloudFormation Console. Below is the method using the CloudFormation Console:

1. **Obtain an AI Service API Key**
   - Acquire an API key from [OpenAI](https://openai.com/) or another AI service whose endpoints you plan to use.
   - Store the API key in AWS Systems Manager Parameter Store.
     - Navigate to the **Parameter Store** in the AWS Console.
     - Create a new parameter and securely store your API key.

2. **Upload Lambda Function ZIP Files**
   - Upload the ZIP files for your Lambda functions ([`ListImages.zip`](https://github.com/Ramil-code/ai-mystery-game/blob/main/ListImages.zip), [`GetDescription.zip`](https://github.com/Ramil-code/ai-mystery-game/blob/main/GetDescription.zip), [`GetImage.zip`](https://github.com/Ramil-code/ai-mystery-game/blob/main/GetImage.zip) to any S3 bucket of your choice.
   - Note the S3 bucket name and API key alias, as you'll need to reference them in the SAM template.

3. **Update SAM Template**
   - Modify the [`template.yaml`](https://github.com/Ramil-code/ai-mystery-game/blob/main/Serverless%20Template.yaml) file to point to the new S3 bucket where your Lambda ZIP files are stored.

4. **Deploy via CloudFormation Console**
   - Go to the **CloudFormation** service in the AWS Console.
   - Click **Create Stack** > **With new resources (standard)**.
   - Upload your [SAM template](https://github.com/Ramil-code/ai-mystery-game/blob/main/Serverless%20Template.yaml)
   - Provide the required parameters:

    
| **Parameter**        | **Type** | **Default**              | **Description**                                       |
|----------------------|----------|--------------------------|-------------------------------------------------------|
| `BucketName`         | String   | `my-default-bucket-name` | Name of the S3 bucket to store your project.         |
| `DynamoTableName`    | String   | `my-default-dynamo-table`| Name of the DynamoDB table for the game data.         |
| `StageName`          | String   | `Prod`                   | Deployment stage name (e.g., Prod, Dev, Test).        |
| `MemorySize`         | Number   | `3008`                   | Memory allocated to Lambda functions (in MB).         |
| `Timeout`            | Number   | `30`                     | Timeout for Lambda functions (in seconds).            |
| `SSMParameterName`   | String   | *Required*               | Name of the SSM Parameter for AI API keys             |

5. **Configure S3 Bucket for the Game**
   - Navigate to created S3 bucket.
   - Create a folder named `photos`.
   - Upload `1.png`, `2.png`, `3.png` from your [`png.zip`](https://github.com/Ramil-code/ai-mystery-game/blob/main/png.zip) archive into the `photos` folder.
   - Upload `placeholder.png` to the root of the S3 bucket.

6. **Set Bucket Policy for Public Access**
   - In the S3 bucket, go to the **Permissions** tab.
   - Edit the **Bucket Policy** to allow public read access to the `photos` folder:
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [
         {
           "Effect": "Allow",
           "Principal": "*",
           "Action": "s3:GetObject",
           "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/photos/*"
         }
       ]
     }
     ```
     - Replace `YOUR_BUCKET_NAME` with the actual name of your S3 bucket.

7. **Update HTML File and upload it to S3 bucket root**
   - Modify the [HTML file](https://github.com/Ramil-code/ai-mystery-game/blob/main/index.html) to include the three API endpoints and the link to `placeholder.png`.
   - Ensure that the endpoints correspond to:
     - `/list-images`
     - `/get-description`
     - `/process`
8. **Access the Game**
   - The link to the game can be found in the **Static Website Hosting** section of your S3 bucket's properties. Navigate to your S3 bucket in the AWS Console, go to the **Properties** tab, and under **Static website hosting**, you'll find the **Endpoint URL**. Open this URL in your browser to start playing the game.

<p align="center">
  <img src="https://github.com/user-attachments/assets/215a1e1c-5c37-4f1d-84a4-e23c492b5c70" alt="Mystery_2" />
</p>


### Customization

**Browser-Based AI Crossword Puzzle** - You can use this template to implement games tailored to your specific theme. 

Here's how to customize and deploy the updated application:


1. **Replace Placeholder Image**
   - Upload your custom image and replace `Placeholder.png` in the root of your S3 bucket with your new image.

2. **Update Environment Variables**
   - In the `GetDescription` Lambda, update the environment variables to include your list of tasks or challenges.
   - In the `GetDescription` Lambda, modify the prompt used by the AI (e.g., DALL-E) if necessary to better fit your game's theme.


## License

This project is licensed under the [MIT License](LICENSE).
