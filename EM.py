import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import base64


class EM_class:
    def __init__(self):
        pass
    #-------------------- SEND EMAIL ----------------------------------------------------
    def send_email_with_form_link(self, record_unsentModules, df_forms):   
        email=record_unsentModules.get('email')
        print(email)

        with open("logo.jpg", "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        # Sender's email and app-specific password
        sender_email = "info.masterminding@gmail.com"
        sender_password = "sgwj tnsf sdzx fsjm"

        # Email server configuration
        smtp_server = "smtp.gmail.com"
        smtp_port = 587

        # Create the email message
        message = MIMEMultipart()
        message["From"] = f"Francesco from Masterminding <sender_email>"
        message["To"] = email
        message["Subject"] = f"Masterminding Educational Intelligence for {record_unsentModules.get('first_name')} {record_unsentModules.get('last_name')}"
        
        # Generating the list items for each subtopic and form_url with "Module n" prefix
        #links_list = "".join([f'<li>Module {i+1}: <a href="{url}" target="_blank">{topic}</a></li>' for i, (topic, url) in enumerate(zip(learningPath, df_forms))])
        #links_list = "".join([f'<li>Module {i+1}: <a href="{url}" target="_blank">{topic.replace('"', '')}</a></li>' for i, (topic, url) in enumerate(zip(learningPath, df_forms))]

        # Initialize an empty list to hold the link items
        links_items = []

        # Iterate over each subtopic and corresponding form URL
        for i, (topic, url) in enumerate(zip(df_forms['module_title'], df_forms['form_url'])):
            # Replace double quotes in the topic with nothing
            try:
                sanitized_topic = topic.replace('"', '')
            except:
                print(f"Error sanitizing topic: {topic}")
                sanitized_topic = topic
            # Construct the list item string for each module
            list_item = f'<li>Module {i+1}: <a href="{url}" target="_blank">{sanitized_topic}</a></li>'
            
            # Append the constructed list item to the links_items list
            links_items.append(list_item)

        # Join all the list items into a single string with newlines for readability (optional)
        links_list = "\n".join(links_items)

        # Email body
        body = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Masterminding: Educational Intelligence</title>
        <style>
            body {
                font-family: Helvetica, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f4f4;
            }
            .container {
                max-width: 600px;
                margin: auto;
                background-color: #fff;
                padding: 20px;
            }
            .footer {
                width: 100%;
                background-color: #fff; /* Adjust this if you have a specific footer background color */
                margin-top: 30px;
            }
            .footer img {
                width: 100%;
                height: auto;
            }
            h2 {
                color: #000fff;
                text-align: center;
            }
            h3, h4 {
                color: #000000;
            }
            p {
                color: ##000000;
            }
            .bold {
                font-weight: bold;
            }
        </style>
        </head>
        <body>
        <div class="container">
            <div style="text-align: center;">
            <h3>Enhance Your Classroom Experience with</h3>
            <h2>Masterminding Educational Intelligence</h2>
            </div>
            """f"""
            <p style="white-space: pre-wrap;">Dear Teacher {record_unsentModules.get('last_name')},</p>
            <p>I hope this email finds you well. 
            <p>Leveraging the insights from your curriculum data submitted on our website, we've meticulously crafted interactive learning modules. These modules, enriched with captivating videos and quizzes, are tailored to deepen students' grasp of <strong><u>{record_unsentModules.get('goal')}</u></strong>, resonating with your educational goals.</p>
            <h4>Highlights of Your Customized Toolkit</h4>
            <ul>
                <li><strong>{i+1} Form Links:</strong> Each form link leads to a dedicated learning module designed around a key concept or learning objective within your curriculum. Here’s what each module offers:
                    <ul>
                        <li><strong>Engaging Videos:</strong> Short, compelling videos that capture essential concepts and demonstrate real-world applications.</li>
                        <li><strong>Interactive Quizzes:</strong> A series of quizzes following each video to test comprehension and reinforce learning, providing immediate feedback.</li>
                    </ul>
                </li>
            </ul>
            <br>
            <p><strong>Your Learning Goals, Our Priority:</strong></p>
            <p>Our aim is to support your educational objectives by providing resources that cater to diverse learning styles. Whether it's simplifying complex theories or offering practice exercises, these modules are designed to help your students achieve mastery in the subject matter.</p>
            <br>
            <p><strong>Getting Started:</strong></p>
            <p>To access these resources, simply click on the links below:</p>"""f"""
            <ul>
                {links_list}
            </ul>
            <br>
            <p><strong>Support and Questions:</strong></p>"""f"""
            <p>Should you have any questions or require further assistance, please do not hesitate to contact our support team at info.masterminding@gmail.com</p>
            <p>We are committed to your success and the academic achievements of your students. Thank you for your dedication to education and for considering Masterminding as a partner in your teaching journey.</p>
            <p>Warm regards,</p>
            <p class="bold">Francesco Rosciano<br>Masterminding Team<br>info.masterminding@gmail.com</p>
            <img src="data:image/jpeg;base64,{base64_image}" alt="Masterminding Logo" style="width: 100px; display: float: left;">
        </div>
        
        
        </body>
        </html>
        """
        message.attach(MIMEText(body, "html"))

        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()  # Upgrade the connection to secure TLS
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, message.as_string())
            server.quit()
            print("---------------------------- EMAIL SENT SUCESSFULLY! -----------------------------------------------------------------------")
        except Exception as e:
            print(f"Failed to send email: {e}")

