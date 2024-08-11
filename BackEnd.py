import requests
from airtable import Airtable
from YT import YT_class
import re
import pandas as pd
import numpy as np
import asyncio
import aiohttp
from datetime import datetime

class BackEnd_class:
    def __init__(self, client, tf_api_key, airtable_key):
        self.client = client
        self.tf_api_key = tf_api_key
        self.airtable_key = airtable_key
        self.answers_dict = {
            "grade": "0522e664-763b-442d-9958-e6537b61a0f0",
            "goal": "cba3f4b2-58b7-449d-8a32-4d9c9e3484d3",
            "sub_goal_(bool)": "0e8ca688-7973-452e-ac1d-1b93438b7a22",
            "sub_goal_(text)": "9cd502df-18b2-4a82-8e53-a574ce688345",
            "preparation": "0918e7f7-7d81-40e2-9f84-5eeafa247cdf",
            "length": "9208e731-a9a4-4a70-9e40-365c5ffc250a",
            "school": "601f7f0a-066b-4157-b98e-966ec8932119",
            "first_name": "c751e53d-306d-483a-a410-fa8f24e2fb2a",
            "last_name": "be8c03c9-c530-45ee-924e-0a0dc4f29f46",
            "email": "e85ddde2-4e7b-425f-8a8a-bc2149fa9a9e"
        }
        self.form_id = "TbTudQc6"

    def fetch_typeform_df(self):
        headers = {"Authorization": f"Bearer {self.tf_api_key}", "Content-Type": "application/json"}
        response = requests.get(f"https://api.typeform.com/forms/{self.form_id}/responses", headers=headers)

        if response.status_code == 200:
            responses = response.json().get("items", [])
            data = []
            if responses:
                for idx, item in enumerate(responses[::-1], start=1):
                    response_data = {
                        'response_id': item.get('response_id'),
                        'submitted_at': item.get('submitted_at')
                    }
                    for answer in item['answers']:
                        field_ref = answer['field']['ref']
                        key = next((k for k, v in self.answers_dict.items() if v == field_ref), None)
                        if key:
                            answer_type = answer['type']
                            if answer_type == 'text':
                                response_data[key] = answer.get('text')
                            elif answer_type == 'boolean':
                                response_data[key] = answer.get('boolean')
                            elif answer_type == 'number':
                                response_data[key] = answer.get('number')
                            elif answer_type == 'choice':
                                response_data[key] = answer['choice']['label']
                            elif answer_type == 'email':
                                response_data[key] = answer.get('email')

                    data.append(response_data)
            df = pd.DataFrame(data).set_index("response_id")
            self.df_TF=df
            return df
        else:
            print(f"ERROR TO RETRIEVE INFO FROM TYPEFORM: {response.status_code}")
            return None

    def fetch_airtable_df(self):
        name="TeachersRecords"        
        endpoint = f"https://api.airtable.com/v0/applQgLxdR4Hh4MIC/{name}"
        headers = {
            "Authorization": f"Bearer {self.airtable_key}",
            "Content-Type": "application/json"}
        
        response = requests.get(endpoint, headers=headers)

        if response.status_code == 200:
            data=response.json()
            fields_data = [record['fields'] for record in data['records']]
            df_TeachersRecords = pd.DataFrame(fields_data)    
            self.df_TeachersRecords=df_TeachersRecords
            return df_TeachersRecords
        else:
            print(response.text) 

    def generate_dalle_image(self,subject):
        response = self.client.images.generate(
            model="dall-e-3",
            prompt=f'''generate me an image to put as a cover of a module to learn "{subject}" for high school students.''',
            size="1024x1024",quality="standard", n=1)
        return response.data[0].url
    
    def updating_df_with_new_entries(self):
    #Insert the new entries in the TeachersRecords table 

        existing_ids = self.df_TeachersRecords['response_id'].tolist()
        new_entries = self.df_TF[~self.df_TF.index.isin(existing_ids)]
        if not new_entries.empty:
            new_records = new_entries.reset_index().to_dict('records')
            for record in new_records:
                fields = {key: value for key, value in record.items() if pd.notna(value)}
                
                #creating the image
                url = self.generate_dalle_image(fields['goal'])
                fields['cover'] = [{'url': url}]

                response = requests.post(
                    "https://api.airtable.com/v0/applQgLxdR4Hh4MIC/TeachersRecords",
                    headers={"Authorization": f"Bearer {self.airtable_key}", "Content-Type": "application/json"},
                    json={"fields": fields}
                )
                if response.status_code == 200:
                    pass
                else:
                    print(f"Failed to add record to Airtable: {response.text}")
        else: 
            print("No new entry for the backend file")

    def get_df_unsentModules(self):
        self.fetch_airtable_df()
        if self.df_TF.empty:
            self.fetch_typeform_df()
        if self.df_TeachersRecords.empty:
            self.fetch_airtable_df()
        df_unsentModules = self.df_TeachersRecords[self.df_TeachersRecords['email_sent'].replace('', np.nan).isna()]
        self.df_unsentModules=df_unsentModules
        return df_unsentModules
    

    
    def create_quiz_with_scoring(self, record_unsentModules, subtopic, video_link, video_description, quiz_matrix, counter=0):
        counter+=1
        workspace_name = f"{record_unsentModules['school']}-{record_unsentModules['last_name']}"
        workspace_name = workspace_name.lower().replace(' ', '_')
        workspace_id = self.find_or_create_workspace(workspace_name)
        
        typeform_api_url = "https://api.typeform.com/forms"
        headers = {
            "Authorization": f"Bearer {self.tf_api_key}",
            "Content-Type": "application/json"
        }

        # Initialize the form data structure
        form_data = {
            "title": f"{record_unsentModules['school']}_{record_unsentModules['last_name']}_{record_unsentModules['grade']}_{counter}",
            "workspace": {
                "href": f"https://api.typeform.com/workspaces/{workspace_id}"
            },
            "type": "score",
            "welcome_screens": [{
                "title": f"Welcome to the module {counter}",
                "properties": {
                    "description": f"{subtopic}",
                    "show_button": True,
                    "button_text": "Start"
                }
            }],
            "fields": [],
            "logic": [],
            "thankyou_screens": [{
                "title": "Thanks for participating!",
                "properties": {
                    "show_button": False,
                    "description": "You got {{var:score}}/10"
                }
            }],
            "variables": {
                "score": 0
            }
        }

        # Add a video field if a video link is provided
        if video_link:
            #add screen to collect student's info
            form_data["fields"].append(
            {"properties": {
                "description": "Please use your academic email!",
                "fields": [
                    {
                        "subfield_key": "first_name",
                        "title": "First name",
                        "type": "short_text",
                        "validations": {
                            "required": True
                        }
                    },
                    {
                        "subfield_key": "last_name",
                        "title": "Last name",
                        "type": "short_text",
                        "validations": {
                            "required": True
                        }
                    },
                    {
                        "subfield_key": "email",
                        "title": "Email",
                        "type": "email",
                        "validations": {
                            "required": False
                        }
                    }
                ]
            },
            "title": "Provide your info to let the teacher know your results :)",
            "type": "contact_info"
        })

            #add screen with yt video
            form_data["fields"].append({
                "title": "Watch this video before starting the quiz",
                "properties": {
                    "description": video_description,
                    "button_text": "Continue",
                    "hide_marks": False
                },
                "type": "statement",
                "attachment": {
                    "type": "video",
                    "href": video_link
                }
            })


        for i, (question, *options) in enumerate(quiz_matrix):
            question_ref = re.sub(r'[^a-zA-Z0-9_-]', '', question)[:254] or f"question_{i}"
            choices = []
            for j, option in enumerate(options):
                # Generate a unique reference for each choice
                option_ref = f"{question_ref}_option_{j}"
                choices.append({
                    "label": option,
                    "ref": option_ref  
                })
                
            question_field = {
                "title": question,
                "ref": question_ref,
                "type": "multiple_choice",
                "properties": {
                    "description": "Your actual score is: {{var:score}}",
                    "randomize": True,
                    "allow_multiple_selection": False,
                    "allow_other_choice": False,
                    "vertical_alignment": True,
                    "choices": choices
                }
            }
            form_data["fields"].append(question_field)

            # Assuming the first option is correct, save its ref for the correct_option_ref
            correct_option_ref = choices[0]["ref"]  # Use the ref of the first choice as the correct option ref

            logic_action = {
                "type": "field",
                "ref": question_ref,
                "actions": [{
                    "action": "add",
                    "details": {
                        "target": {
                            "type": "variable",
                            "value": "score"
                        },
                        "value": {
                            "type": "constant",
                            "value": 1
                        }
                    },
                    "condition": {
                        "op": "is",
                        "vars": [
                            {"type": "field", "value": question_ref},
                            {"type": "choice", "value": correct_option_ref}  # Use the generated choice ref
                        ]
                    }
                }]
            }
            
            form_data["logic"].append(logic_action)

        response = requests.post(typeform_api_url, json=form_data, headers=headers)
        
        if response.status_code == 201:
            response_data = response.json()
            form_url = response_data.get("_links", {}).get("display", "")
            form_id = response_data.get("id", "")
            module_title = response_data.get("welcome_screens", [{}])[0].get("properties", {}).get("description", "")
            #print(f"------------------------- FORM CREATED SUCCESFULLY -------------------------")
            #print(f"{form_url}")
            return form_id, form_url, module_title, workspace_id
        else:
            print(f"Failed to create the quiz. Redo the quiz")
            model = "gpt-3.5-turbo-16k-0613" 
            YouTubeSearch = YT_class(self.client, subtopic, record_unsentModules)
            structured_description = YouTubeSearch.generate_description(video_description, video_description, record_unsentModules)
            OA_class = OA_class(self.client, model, record_unsentModules)
            quiz_matrix=OA_class.generate_quiz_json(structured_description,subtopic)
            workspace_id, form_id, form_url, module_title = self.create_quiz_with_scoring(record_unsentModules, subtopic, video_link, structured_description, quiz_matrix, counter)
            
            return form_id, form_url, module_title, workspace_id

    def find_or_create_workspace(self, workspace_name):
        
        headers = {
            "Authorization": f"Bearer {self.tf_api_key}",
            "Content-Type": "application/json"
        }
        url = "https://api.typeform.com/workspaces"
        
        # Fetch existing workspaces
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            workspaces = response.json().get('items', [])
            for workspace in workspaces:
                if workspace['name'] == workspace_name:
                    return workspace['id']  # Return existing workspace ID

        # Create a new workspace if not found
        data = {
            "name": workspace_name
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 201:
            workspace = response.json()
            return workspace['id']  # Return new workspace ID
        else:
            print(f"Failed to create workspace. Error: {response.text}")
            return None

    #--------------------------------------------------------------------------------------------------------------------------------
    #-------------------- UPDATED AIRTABLE EMAIL STATUS AND WORKSPACE LINK COLUMN ---------------------------------------------------
    #--------------------------------------------------------------------------------------------------------------------------------
    def update_airtable_email_status(self, response_id, workspace_id):
        airtable = Airtable('applQgLxdR4Hh4MIC', 'TeachersRecords', self.airtable_key)
        records = airtable.get_all(formula=f"{{response_id}} = '{response_id}'")
        if records:
            record_id = records[0]['id']
            update_fields = {
                'email_sent': 'yes', 
                "workspace_link": f"https://admin.typeform.com/accounts/01HN8QVPHG65DWDDGQGC1Q47DK/workspaces/{workspace_id}", 
                "workspace_id": f"{workspace_id}"}
            airtable.update(record_id, update_fields)
            print("Record updated successfully.")
        else:
            print("No matching records found.")

        
    def update_airtable_all_modules_sent(self, df_forms_single_record):
        url = f"https://api.airtable.com/v0/applQgLxdR4Hh4MIC/AllModulesSent"
        headers = {
            'Authorization': f'Bearer {self.airtable_key}',
            'Content-Type': 'application/json'
        }
        records = []

        for _, row in df_forms_single_record.iterrows(
        ):
            record = {
                'fields': {
                    'form_id': row['form_id'],
                    'form_url': row['form_url'],
                    'module_title': row['module_title'],
                    'learning_goal': row['learning_goal'],
                    'response_id': row['response_id'],
                    'first_name': row['first_name'],
                    'last_name': row['last_name'],
                    'email': row['email'],
                    'length': row['length'],
                    'preparation': row['preparation'],
                    'grade': row['grade'],
                    'workspace_id': row['workspace_id'],
                    'time_sent': row['time_sent'],
                    'module_index': row['module_index']
                }
            }


            records.append(record)
        
        chunk_size = 10
        for i in range(0, len(records), chunk_size):
            chunk_records = records[i:i+chunk_size]
            requests.post(url, headers=headers, json={'records': chunk_records})
    

    async def update_airtable_students_records(self):
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.airtable_key}", "Content-Type": "application/json"}
            
            async def fetch_all_records(url):
                all_records = []
                offset = None
                while True:
                    params = {'pageSize': 100}
                    if offset:
                        params['offset'] = offset
                    async with session.get(url, headers=headers, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            all_records.extend(data['records'])
                            if 'offset' in data:
                                offset = data['offset']
                            else:
                                break
                        else:
                            print(f"Error fetching records: {await response.text()}")
                            return []
                return all_records

            # Fetch StudentsRecords
            url_StudentsRecords = "https://api.airtable.com/v0/applQgLxdR4Hh4MIC/StudentsRecords"
            students_records = await fetch_all_records(url_StudentsRecords)
            df_StudentsRecords = pd.DataFrame([record['fields'] for record in students_records])
            StudentsRecords_ids_already_inserted = df_StudentsRecords["student_response_id"].tolist() if not df_StudentsRecords.empty else []
            
            # Fetch AllModulesSent
            url_AllModulesSent = "https://api.airtable.com/v0/applQgLxdR4Hh4MIC/AllModulesSent"
            all_modules_sent = await fetch_all_records(url_AllModulesSent)
            df_AllModulesSent = pd.DataFrame([record['fields'] for record in all_modules_sent])

            # Get list of form IDs from df_AllModulesSent
            AllModulesSent_form_ids = df_AllModulesSent['form_id'].tolist()

            async def process_form(module_form_id, df_AllModulesSent, index):
                typeform_headers = {"Authorization": f"Bearer {self.tf_api_key}", "Content-Type": "application/json"}
                url = f"https://api.typeform.com/forms/{module_form_id}/responses"
                async with session.get(url, headers=typeform_headers) as response:
                    print(f"Proceeding with {index + 1}: {module_form_id}")
                    response_text = await response.text()
                    
                    if response.status != 200:
                        print(f"Error fetching form responses: {response_text}")
                        return None
                    
                    data = await response.json()
                    responses_student_form = data.get("items", [])
                    
                    if not responses_student_form:
                        return None

                    total_time = 0
                    response_count = 0
                    records_StudentsRecords = []
                    total_score = 0
                    
                    for i, response_data in enumerate(responses_student_form):


                        print(f"\tGET RESPONSE {i+1} of {response_data.get('response_id')}")
                        response_id = response_data.get("response_id")


                        landed_at = datetime.fromisoformat(response_data.get("landed_at").replace('Z', '+00:00'))
                        submitted_at = datetime.fromisoformat(response_data.get("submitted_at").replace('Z', '+00:00'))
                        time_to_complete = (submitted_at - landed_at).total_seconds()
                        
                        total_time += time_to_complete
                        response_count += 1

                        if response_id not in StudentsRecords_ids_already_inserted:

                            score = response_data.get("calculated", {}).get("score")
                            print(f"score: {score}")
                            total_score += score if score is not None else 0

                            record = {
                                'fields': {
                                    'student_response_id': response_id,
                                    'name': response_data.get("answers")[0].get("text"),
                                    'last_name': response_data.get("answers")[2].get("text"),
                                    'email': response_data.get("answers")[1].get("email"),
                                    'score': score,
                                    'time_to_complete': int(time_to_complete),
                                    'form_id': module_form_id,
                                    'form_title': df_AllModulesSent.loc[df_AllModulesSent['form_id'] == module_form_id, 'module_title'].iloc[0],
                                    'form_learning_goal': df_AllModulesSent.loc[df_AllModulesSent['form_id'] == module_form_id, 'learning_goal'].iloc[0],
                                    'teacher_email': df_AllModulesSent.loc[df_AllModulesSent['form_id'] == module_form_id, 'email'].iloc[0],
                                    'module_index': df_AllModulesSent.loc[df_AllModulesSent['form_id'] == module_form_id, 'module_index'].iloc[0]
                                }
                            }
                            records_StudentsRecords.append(record)


                    # Update StudentsRecords table
                    chunk_size = 10
                    for i in range(0, len(records_StudentsRecords), chunk_size):
                        chunk_records = records_StudentsRecords[i:i+chunk_size]
                        async with session.post(url_StudentsRecords, headers=headers, json={'records': chunk_records}) as post_response:
                            print(f"Status Code: {post_response.status}, Response: {await post_response.text()}")

                    student_submissions = len(responses_student_form)
                    student_average_time_to_complete = total_time / response_count if response_count > 0 else 0

                    student_average_score = total_score / response_count if response_count > 0 else 0
                    print(f"student_average_score: {student_average_score}")
                    
                    # Fetch incomplete responses
                    params = {'completed': 'false'}
                    async with session.get(url, headers=typeform_headers, params=params) as incomplete_response:
                        incomplete_data = await incomplete_response.json()
                        student_unsubmissions = len(incomplete_data.get("items", []))
                    
                    student_start = student_unsubmissions + student_submissions

                    return {
                        'module_form_id': module_form_id,
                        'student_start': student_start,
                        'student_submissions': student_submissions,
                        'student_average_time_to_complete': int(student_average_time_to_complete),
                        'student_average_score': student_average_score
                    }

            # Process forms
            tasks = [process_form(module_form_id, df_AllModulesSent, index) for index, module_form_id in enumerate(AllModulesSent_form_ids)]
            results = await asyncio.gather(*tasks)

            # Update AllModulesSent table
            airtable = Airtable('applQgLxdR4Hh4MIC', 'AllModulesSent', self.airtable_key)
            for result in results:
                if result:
                    records = airtable.get_all(formula=f"{{form_id}} = '{result['module_form_id']}'")
                    if records:
                        record_id = records[0]['id']
                        update_fields = {
                            'student_start': result['student_start'],
                            'student_submissions': result['student_submissions'],
                            'student_average_time_to_complete': result['student_average_time_to_complete'],
                            'student_average_score': result['student_average_score']
                        }
                        airtable.update(record_id, update_fields)
                        print(f"Record updated successfully for form_id: {result['module_form_id']}")
                    else:
                        print(f"No matching records found for form_id: {result['module_form_id']}")

            print("All records processed and updated.")