from concurrent.futures import ThreadPoolExecutor, as_completed
from BackEnd import BackEnd_class
from OA import OA_class
from YT import YT_class
from EM import EM_class
import pandas as pd
import os
import time
from openai import OpenAI
import sys
from contextlib import redirect_stdout
from progressbar import progressbar
import asyncio


openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY is not set in environment variables")

tf_api_key = os.getenv('TYPEFORM_API_KEY')
if not tf_api_key:
    raise ValueError("TYPEFORM_API_KEY is not set in environment variables")

airtable_key = os.getenv('airtable_key')
if not airtable_key:
    raise ValueError("airtable_key is not set in environment variables")

client = OpenAI(api_key=openai_api_key)
model = "gpt-4o-mini"  

# ----- BE_class -----
BE_class = BackEnd_class(client, tf_api_key, airtable_key)
# ----- EM_CLASS -----
EmailSender = EM_class()

def process_subtopic(subtopic, client, record_unsentModules, OpenAI_class, BE_class, YouTubeSearch, i):
    video_link, video_title, video_description, video_transcript = YouTubeSearch.find_best_matching_video()
    structured_description = YouTubeSearch.generate_description(video_transcript, video_description)

    ## generating quiz
    quiz_matrix = OpenAI_class.generate_quiz_json(structured_description, subtopic)
    if quiz_matrix is None:
        quiz_matrix = OpenAI_class.generate_quiz_json(structured_description, subtopic)

    ## quiz post and fetching of form's info
    form_id, form_url, module_title, workspace_id = BE_class.create_quiz_with_scoring(record_unsentModules, subtopic, video_link, structured_description, quiz_matrix, i)
    return form_id, form_url, subtopic, record_unsentModules, workspace_id

def process_record(record_unsentModules, client, model, BE_class, EmailSender):
    OpenAI_class = OA_class(client, model, record_unsentModules)
    record_unsentModules_dict = record_unsentModules.to_dict()
    learningPath = OpenAI_class.learningPath_generator()
    df_forms_single_record = pd.DataFrame(index=range(len(learningPath)), 
                                          columns=['form_id', 'form_url', 'module_title', 'learning_goal', 'response_id', 
                                                   "first_name", "last_name", "email", 
                                                   'goal', 'length', 'preparation', 
                                                   'grade', 'time_sent', "workspace_id","module_index"])

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_subtopic, subtopic, client, record_unsentModules_dict, OpenAI_class, BE_class, YT_class(client, subtopic, record_unsentModules_dict), i) for i, subtopic in enumerate(learningPath)]
        results = [future.result() for future in as_completed(futures)]
        for result in results:
            form_id, form_url, subtopic, record_unsentModules_dict, workspace_id = result
            df_forms_single_record.loc[learningPath.index(subtopic)] = [form_id, form_url, subtopic, record_unsentModules_dict['goal'], record_unsentModules_dict['response_id'], 
                                                                        record_unsentModules_dict['first_name'], record_unsentModules_dict['last_name'], record_unsentModules_dict['email'], 
                                                                        record_unsentModules_dict['goal'], record_unsentModules_dict['length'], record_unsentModules_dict['preparation'], 
                                                                        record_unsentModules_dict['grade'], time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), workspace_id, f"Unit {learningPath.index(subtopic)+1} of {len(learningPath)}"]
            
    EmailSender.send_email_with_form_link(record_unsentModules_dict, df_forms_single_record)
    BE_class.update_airtable_all_modules_sent(df_forms_single_record)
    BE_class.update_airtable_email_status(record_unsentModules_dict['response_id'], workspace_id)

async def main_loop():
    cycle_number = 0
    while True:
        BE_class.fetch_typeform_df()
        BE_class.fetch_airtable_df()
        BE_class.updating_df_with_new_entries()
        df_unsentModules = BE_class.get_df_unsentModules()

        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(process_record, record_unsentModules, client, model, BE_class, EmailSender) for _, record_unsentModules in df_unsentModules.iterrows()]
            for future in as_completed(futures):
                future.result()
        
        # Run the asynchronous update_airtable_students_records function
        await BE_class.update_airtable_students_records()

        cycle_number += 1
        print(f"Cycle {cycle_number}: Waiting for 3 minutes before the next check...")
        await asyncio.sleep(180)

if __name__ == "__main__":
    asyncio.run(main_loop())

