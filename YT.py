import re
from youtubesearchpython import VideosSearch, Video, Transcript, ResultMode

class YT_class:
    def __init__(self, client, subtopic, record_unsentModules):
        self.client = client
        self.subtopic = subtopic
        self.record_unsentModules = record_unsentModules
    #-------------------- FIND YT VIDEO ----------------------------------------------------
    def find_best_matching_video(self):

        search_query_GPT = self.client.chat.completions.create(
            model="gpt-4o-mini",  
            messages=[
                {"role": "system", "content": f'You are a teacher that is searching YouTube educational videos about "{self.subtopic}" for your students who have the ultimate learning goal: "{self.record_unsentModules["goal"]}"'},
                {"role": "user", "content": f'Generate keywords for a YouTube search targeting educational and engaging videos with the goal of learning "{self.subtopic}" for {self.record_unsentModules["grade"]} students with a proficiency level of {self.record_unsentModules["preparation"]} out of 10. You must generate keywords that are strictly related to "{self.subtopic}" and nothing else. Do not output any introduction or accessory text, you must output only keywords separated by spaces only'}
            ],temperature=0.25,max_tokens=40,top_p=1,frequency_penalty=0,presence_penalty=1)

        generated_query = search_query_GPT.choices[0].message.content
        print(generated_query)
        keywords=generated_query + " " + self.subtopic + " " + self.subtopic + " " + self.subtopic + " " + self.subtopic + " " + self.subtopic

        videosSearch = VideosSearch(generated_query, limit=15)
        search_results = videosSearch.result()

        
        matching_videos = []

        for video in search_results['result']:
            view_count = int(video.get('viewCount', {}).get('text', '0').replace(' views', '').replace(',', ''))
            matching_score = 0
            try:
                matching_score += sum(word in video['title'].lower() for word in keywords.lower().split())
            except:
                print("Error in processing video title")
                pass
            try:
                matching_score += sum(word in video['descriptionSnippet'][0]['text'].lower() for word in keywords.lower().split())
            except:
                print("Error in processing video description")
                pass
            try:
                matching_score += sum(word in video.get('keywords', '').lower() for word in keywords.lower().split())
            except:
                print("Error in processing video keywords")
                pass
            duration = video['duration']
            total_seconds = sum(x * int(t) for x, t in zip([3600, 60, 1], re.findall(r'\d+', duration)))
            print(f"Video ID: {video['id']}, Matching Score: {matching_score}, Duration: {duration}, Total Seconds: {total_seconds}, View Count: {view_count}")
            print(f"\nVIDEO\n{video}\n\n")
            video_id=video['id']

            matching_videos.append((video_id, matching_score, total_seconds, view_count, video['link'], video['title']))

        # select the 5 videos with the highest view count
        matching_videos.sort(key=lambda x: -x[3])
        top_videos = matching_videos[:5]
        # select the 5 videos with the highest matching score
        top_videos.sort(key=lambda x: -x[1])
        top_videos = top_videos[:3]
        #select the shortest video
        top_videos.sort(key=lambda x: x[2])
        top_videos = top_videos[:1]
        try:
            video_id = top_videos[0][0]
            print(f"Selected video ID: {video_id}")
        except IndexError:
            print("No videos found in top_videos list. Retrying...")
            return self.find_best_matching_video()
        
        video_link = top_videos[0][4]
        video_title = top_videos[0][5]

        try:
            video_info = Video.getInfo(video_id=video_id)
            video_description = video_info['description']
        except Exception as e:
            print(f"Error getting video info: {str(e)}")
            try:
                video = Video.get(video_link)
                video_description = video['description']      
                if not video_description:
                    print("Video description not found. Using title as fallback.")
                    video_description = video_title
            except:
                print("Error getting video description")
                video_description = video_title

        try:
            transcript = Transcript.get(video_link)
        except Exception as e:
            print(f"Error getting transcript: {str(e)}")
            transcript = video_description

        print("------------------------- Video found. -------------------------")
        return video_link, video_title, video_description, transcript

    #-------------------- VIDEO DESCRIPTION ----------------------------------------------------
    def generate_description(self, video_transcript, video_description):
       
        teacher=f"Act as a teacher that explain things in the most simple way to student of {self.record_unsentModules['grade']} that from 0 (don't know anything) to 10 (know everything about) are prepared student of {self.record_unsentModules['preparation']}. You MUST output only the content without any introduction."
        
        description_prompt = f'''Given the video transcript provided, create a structured description that helps a student understand and learn from the video effectively. Follow these guidelines:
                                \n\n
                                \n- Length: Maximum 200 words.
                                \n- Format: Strucutre it in 3 paragraphs, capitalizing title and subtitles. 
                                \n- Content: Tailor the language and explanation to be appropriate for a student in the specified grade ({self.record_unsentModules['grade']}).
                                \n- Focus: Highlight educational and explanatory elements.
                                \n
                                \nYour task is to distill the key information from the transcript into a concise, accessible format suitable for educational purposes.
                                \n
                                \nVideo Transcript: """{video_transcript}"""'''
        try:
            description_response = self.client.chat.completions.create(
                model="gpt-4o-mini",  
                messages=[
                    {"role": "system", "content": teacher},
                    {"role": "user", "content": description_prompt}
                ],temperature=1,max_tokens=150,top_p=1,frequency_penalty=0,presence_penalty=0)

            structured_description = description_response.choices[0].message.content  
        except:
            description_prompt = f'''Given the video transcript provided, create a structured description that helps a student understand and learn from the video effectively. Follow these guidelines:
                                \n\n
                                \n- Length: Maximum 200 words.
                                \n- Format: Strucutre it in 3 paragraphs, capitalizing title and subtitles. 
                                \n- Content: Tailor the language and explanation to be appropriate for a student in the specified grade ({self.record_unsentModules['grade']}).
                                \n- Focus: Highlight educational and explanatory elements.
                                \n
                                \nYour task is to distill the key information from the transcript into a concise, accessible format suitable for educational purposes.
                                \n
                                \nVideo Transcript: """{video_description}"""'''

            description_response = self.client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=[
                    {"role": "system", "content": teacher},
                    {"role": "user", "content": description_prompt}
                ],temperature=1,max_tokens=300,top_p=1,frequency_penalty=0,presence_penalty=0)
            structured_description = description_response.choices[0].message.content  

        print("------------------------- Structured description generated successfully. -------------------------")
        return structured_description
