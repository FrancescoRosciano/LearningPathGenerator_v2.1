import json
import pandas as pd


class OA_class:
    def __init__(self, client, model, record_unsentModules):
        self.model = model
        self.client=client
        self.record_unsentModules=record_unsentModules.to_dict()

    #-------------------- SUBTOPICS ----------------------------------------------------
    def learningPath_generator(self):
        
        teacher = f"Assume the role of a teacher explaining concepts for students in {self.record_unsentModules['grade']} with a knowledge level of {self.record_unsentModules['preparation']} on a scale from 0 (no knowledge) to 10 (full mastery). You MUST output only the content without any introduction."
        if self.record_unsentModules['length'] == "1 hour":
            length = 10
        elif self.record_unsentModules['length']=="30 minutes":
            length=5
        elif self.record_unsentModules['length']=="15 minutes":
            length=3
        else:
            length=10


        if self.record_unsentModules['sub_goal_(bool)']:
            prompt = f'''Given the following learning goal: """{self.record_unsentModules['goal']}""".\nGenerate the most learning efficient path of {length} subtopics that would guide a student to achieve the learning goal """{self.record_unsentModules['goal']}""". You must tailor the learning path for a student of {self.record_unsentModules['grade']} that, from 0 (no knowledge) to 10 (full mastery), are prepared at {self.record_unsentModules['preparation']}.
                        \nEmphasize the sub-topic: """{self.record_unsentModules['sub_goal_(text)']}""", while ensuring all content aligns with the primary learning goal: """{self.record_unsentModules['goal']}""".
                        \nEach sub-topic must be fully descriptive and detailed regarding the sub-learning goal that must be achieved in order to successfully achieve the given learning goal.
                        \nEach sub-topic must be separated only by a single '/' character among subtopics, in a single line of prompt (no dot lists, bullet points, etc.)
                        \nThe output must strictly adhere to the following format: "sub-topic1/sub-topic2/..."
                        \nYour output MUST be formatted EXACTLY as the array with "/" as described before; NO DEVIATION, NO ADDITIONAL CONTENT. Adherence to this structured format is non-negotiable.
                        '''
        else:
            prompt = f'''Given the following learning goal: """{self.record_unsentModules['goal']}""".\nGenerate the most learning efficient path of {length} subtopics that would guide a student to achieve the learning goal """{self.record_unsentModules['goal']}""". You must tailor the learning path for a student of {self.record_unsentModules['grade']} that, from 0 (no knowledge) to 10 (full mastery), are prepared at {self.record_unsentModules['preparation']}.
                        \nEach sub-topic must be fully descriptive and detailed regarding the sub-learning goal that must be achieved in order to successfully achieve the given learning goal.
                        \nEach sub-topic must be separated only by a single '/' character among subtopics, in a single line of prompt (no dot lists, bullet points, etc.)
                        \nThe output must strictly adhere to the following format: "sub-topic1/sub-topic2/..."
                        \nYour output MUST be formatted EXACTLY as the array with "/" as described before; NO DEVIATION, NO ADDITIONAL CONTENT. Adherence to this structured format is non-negotiable.
                        '''

        response = self.client.chat.completions.create(model=self.model,  
            messages=[
                {"role": "system","content": teacher },
                {"role": "user", "content": prompt}],
            temperature=1,max_tokens=8500,top_p=1,frequency_penalty=0,presence_penalty=0)
        
        learning_path_response = response.choices[0].message.content

        learningPath = learning_path_response.split("/")
        
        '''------------------------- CODE TO ENUMERATE SUBTOPICS -------------------------
        learning_path_formatted = []
        for index, subtopic in enumerate(learning_path, start=1):
            learning_path_formatted.append(f"{index}) {subtopic}")
        learning_path_formatted_str = "/".join(learning_path_formatted)
        learning_path = learning_path_formatted_str.split("/")
        ------------------------------------------------------------------------------'''
        
        if len(learningPath) != length:
            print("STRUCTURE WRONG, calling 'adjust_format_learning_path' ... ")
            for attempt in range(5):
                learningPath = self.adjust_format_learning_path(learning_path_response,length)
                if len(learningPath) == length:
                    break
                print(f"Structure generated wrongly. Attempt: {attempt}")
            else:
                return self.learningPath_generator()
    
        print(f"\n------------------------- LEARNING PATHS GENERATED -------------------------")
        self.learningPath=learningPath
        return learningPath

    def adjust_format_learning_path(self, learning_path_response, length):
        
        adjustment_prompt = f'''Given the learning goal """{self.record_unsentModules['goal']}""" for a student of grade """{self.record_unsentModules['grade']}""" who is currently at a preparation level of """{self.record_unsentModules['preparation']}""" on a scale from 0 (no knowledge) to 10 (full mastery), generate an optimal learning path. This path should be structured as a sequence of 10 sub-topics that transition from basic to advanced, catering to the specified preparation level.
                            YOUR GOAL is to REFORMAT the LEARNING_PATH attached below as a single-line string, listing exactly {length} sub-topics separated only by a '/' character with no spaces before or after each '/'. Do not include any punctuation or additional characters within or between sub-topics. Each sub-topic should succinctly describe a step in the learning progression necessary to achieve the overall goal """{self.record_unsentModules['goal']}""".
                            The output should strictly adhere to this format for it to be directly convertible into an array:
                            "sub-topic1/sub-topic2/sub-topic3/.../sub-topic10"
                            Ensure that the sequence logically progresses in complexity and relevance, offering a comprehensive roadmap from a beginner's perspective to full mastery.
                            Note: The output MUST RIGOROUSLY conform to the described format. Adherence to this structured format is critical and non-negotiable. Adjustments should reorganize the provided content to precisely fit this structure, maintaining the original question and answer essence.
                            LEARNING_PATH:\n"""{learning_path_response}"""
                            '''
        
        adjustment_response = self.client.chat.completions.create(
            model="gpt-3.5-turbo-16k-0613",  
            messages=[
                {"role": "system","content": f"Validate the structured output from ChatGPT against the expected format. The output must be a single line string with {length} sub-topics separated by '/' without spaces. Ensure there are exactly 10 sub-topics, each representing a step towards achieving the learning goal. Confirm the special emphasis on the specified sub-topic. If the output matches the criteria, mark it as valid for array conversion; otherwise, provide feedback on discrepancies." },
                {"role": "user", "content": adjustment_prompt}],
            temperature=0.25, max_tokens=8500, top_p=1, frequency_penalty=0, presence_penalty=0)

        try:
            learning_path_response = adjustment_response.choices[0].message.content
            learning_path = learning_path_response.split("/")
        except:
            return self.adjust_format_learning_path(learning_path_response, length)
        return learning_path
    
#-------------------- CREATE QUIZ ----------------------------------------------------
    def  generate_quiz_json(self, structured_description, subtopic):
        
        teacher = f'''Act as a teacher that explains things simply to students of grade {self.record_unsentModules['grade']} that from 0 (no knowledge) to 10 (full mastery) are prepared {self.record_unsentModules['preparation']}.
                Your response should exclude any introductory comments and directly address the requirements. 
                Use standard mathematical symbols for any formulas.'''   
        
        quiz_prompt = f'''
                        Create a JSON-formatted educational quiz tailored for students in {self.record_unsentModules['grade']} with a preparation level of {self.record_unsentModules['preparation']} out of 10. The quiz should focus on the subtopic '{subtopic}' and consist of 10 questions of increasing difficulty. 

                        - The first three questions should be basic, directly related to the fundamental aspects of the subtopic.
                        - The next four questions should delve into more complex and detailed aspects.
                        - The final three questions should challenge the students with advanced and critical thinking scenarios related to the subtopic.
                        '''+'''
                        Each question should provide four multiple-choice answers formatted as follows:
                        {'question': 'Example Question', 'answers': ['Correct answer', 'Incorrect option 1', 'Incorrect option 2', 'Incorrect option 3']}'''+f'''

                        The first answer must always be the correct one. Ensure that the questions encourage critical thinking and deeper understanding of the subtopic. Adhere strictly to the specified JSON format throughout the quiz.

                        VIDEO DESCRIPTION:\n"""{structured_description}"""'''


        quiz_response = self.client.chat.completions.create(
            model="gpt-3.5-turbo-0125",response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": teacher},
                {"role": "user", "content": quiz_prompt}
            ], temperature=0.25, max_tokens=2000, top_p=1, frequency_penalty=0, presence_penalty=0.75)


        try:
            quiz_json_str = quiz_response.choices[0].message.content
        except KeyError as err:
            print("KeyError: 'text' not found in quiz response.")
            return self.generate_quiz_json(structured_description, subtopic)
        except AttributeError as err:
            print("AttributeError: 'text' not found in quiz response.")
            return self.generate_quiz_json(structured_description, subtopic)
        
        try:
            print("Attempting to load quiz_json...")
            quiz_json = json.loads(quiz_json_str)
            print("Quiz JSON loaded successfully.")
        except json.JSONDecodeError:
            print("JSONDecodeError occurred. Attempting to adjust quiz_json_str...")
            quiz_json_str = quiz_json_str.replace("json", "", 1).replace("JSON", "", 1).replace("quiz", "", 1).replace("Quiz", "", 1).replace("QUIZ", "", 1).strip()
            try:
                quiz_json = json.loads(quiz_json_str)
                print("Adjusted quiz_json_str loaded successfully.")
            except json.JSONDecodeError:
                flag=1
                count = 5
                while flag==1 or count<5:
                    quiz_json, flag = self.adjust_quiz_format_toJSON(quiz_json_str, flag)
                    if flag==1:
                        quiz_json, flag =self.adjust_quiz_format_toJSON(quiz_json, flag)
                    count +=1


        print("Quiz JSON loaded successfully.")
        
        quiz_matrix = []
        try:
            for question in quiz_json:
                row = [question['question']]
                row.extend(question['answers'])
                quiz_matrix.append(row)
        except:
            try:
                quiz_matrix_json= quiz_json['quiz']['questions']
                for question in quiz_matrix_json:
                    row = [question['question']]
                    row.extend(question['answers'])
                    quiz_matrix.append(row)
            except:
                try:   
                    quiz_matrix_json= quiz_json['quiz']
                    for question in quiz_matrix_json:
                        row = [question['question']]
                        row.extend(question['answers'])
                        quiz_matrix.append(row)
                except:
                    try:
                        quiz_matrix_json=quiz_json['questions']
                        for question in quiz_matrix_json:
                            row = [question['question']]
                            row.extend(question['answers'])
                            quiz_matrix.append(row)
                    except:
                        print(quiz_json)
                        return self.generate_quiz_json(structured_description, subtopic)

        print("Quiz matrix created.")
        return quiz_matrix 

    def adjust_quiz_format_toJSON(self, quiz_response_content, flag):
        print("Starting quiz format adjustment...")
        
        adjustment_prompt = '''
                            Please precisely format the following quiz responses into a strict and specific structure for seamless integration into an educational matrix. Each question MUST be formatted EXACTLY as shown below, with NO DEVIATION, NO ADDITIONAL CONTENT:

                            {"question": "INSER THE QUESTION", "answers": ["INSERT THE FIRST ANSWER","INSERT THE SECOND ANSWER","INSERT THE THIRD ANSWER","INSERT THE FOURTH ANSWER"]}

                            A total of 10 questions must be meticulously reorganized to follow this structure. Ensure all necessary components are present, correctly positioned, and strictly adhere to the format without altering the essence of the questions or answers. Below are the quiz responses that require formatting:

                            ''' + f'"""{quiz_response_content}"""' + '''

                            Note: The output MUST RIGOROUSLY conform to the described format. The structure is critical for the content's direct transformation into an educational matrix. Adjustments should reorganize the provided content to precisely fit this structure, maintaining the original question and answer essence.
                            '''

        adjustment_response = self.client.chat.completions.create(
            model="gpt-3.5-turbo-0125",response_format={"type": "json_object"},  # Update the model name based on current availability
            messages=[
                {"role": "system","content": "You are a JSON expert that will output ONLY the JSON structure" },
                {"role": "user", "content": adjustment_prompt}
            ],temperature=0.5,max_tokens=2000,top_p=1,frequency_penalty=0,presence_penalty=0)

        try:
            adjusted_quiz_response = adjustment_response.choices[0].message.content
        except:
            flag=-1
            print("Error: Adjusted quiz response not obtained. Redo")
            self.adjust_quiz_format_toJSON(quiz_response_content, flag)
    
        try:
            quiz_json = json.loads(adjusted_quiz_response)
        except json.JSONDecodeError:
            flag=1
            print("JSONDecodeError occurred while loading adjusted quiz response.")
            return None, 1
    
        flag=0
        print("Quiz format adjustment completed successfully.")
        return quiz_json,flag

