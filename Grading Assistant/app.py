import csv
from flask import Flask, request, render_template, jsonify
import io
import openai


app = Flask(__name__)

question_groups = {} # Dictionary to store question groups


# Route for displaying the exam and processing uploaded CSV
@app.route('/', methods=['GET', 'POST'])
def display_exam():
    global question_groups  # Accessing the global variable

    if request.method == 'POST':
        csv_file = request.files['csv_file']
        encodings = ["utf-8", "utf-8-sig", "latin-1"]
        if csv_file:
            # Read the uploaded CSV file
            content = csv_file.read()
            csv_content = None

            for encoding in encodings:
                try:
                    csv_content = content.decode(encoding)
                    break  # Break out of the loop if decoding is successful
                except UnicodeDecodeError:
                    continue  # Try the next encoding option

            if csv_content is None:
                return "Error: Failed to decode CSV file"

             # Parse CSV content into a dictionary
            reader = csv.DictReader(io.StringIO(csv_content), delimiter=';')
            question_groups = {}

            for row in reader:
                question_id = row['id']
                question = row['question']
                student_id = row['studentID']
                student_answer = row['student_answer']

                # Create or update question groups
                if question_id not in question_groups:
                    question_groups[question_id] = {
                        'question': question,
                        'student_ids': [],
                        'student_answers': []
                    }

                question_groups[question_id]['student_ids'].append(student_id)
                question_groups[question_id]['student_answers'].append(student_answer)

            return render_template('index.html', question_groups=question_groups)

    return render_template('index.html')


# Route for displaying the score window
@app.route('/score_window/<question_group_id>')
def score_window(question_group_id):
 
    return render_template('score_window.html', question_group_id=question_group_id)

# Route for searching and retrieving a student answers
@app.route('/search', methods=['POST'])
def search_student_answer():
    try:
        data = request.get_json()
        student_id = data['studentId']
        question_group_id = data['questionGroupId']  # Added line to get the question group ID

        print('Received student ID:', student_id)
        print('Received question group ID:', question_group_id)

        # Search for the student answer based on the student ID and question group ID
        student_answer = None
        if question_group_id in question_groups:
            question_group = question_groups[question_group_id]
            print('Question group:', question_group)
            if student_id in question_group['student_ids']:
                index = question_group['student_ids'].index(student_id)
                student_answer = question_group['student_answers'][index]
                print('Found student answer:', student_answer)
            else:
                print('Student ID not found:', student_id)
        else:
            print('Question group ID not found:', question_group_id)

        # Return the student's answer as JSON response
        return jsonify({'studentAnswer': student_answer})

    except Exception as e:
        print('Error searching for student answer:', e)
        return jsonify({'error': 'An error occurred while searching for the student answer.'}), 500



# Set OpenAI API key
openai.api_key = 'Enter your API key here'

# Route for ranking student answers based on correctness and quality using ChatGPT
@app.route('/score', methods=['POST'])
def score_student_answers():
    try:
        data = request.get_json()

        student_data = data['student_data']
        question = data['question']
        student_answers = data['student_answers']

        # Creation of empty lists to store results
        scores = []
        feedbacks = []

        for student_answer in student_answers:

            # Prepare the prompt
            
            prompt = f"""Instructions:
            You are an assistant of an instructor in higher education, and you will be assessing the quality of students exam answers based the depth of understanding demonstrated by the students and the correctness of the answer. 
            Each answer should be ranked on a scale from 0 to 5, where 0 represents a poor answer and 5 represents an excellent answer. 
            Point fractions (e.g., 4.5, 3.25) are possible if necessary.
            Also provide constructive feedback in 30 words or less for students not achieving full points: 
            Clearly mention and explain the errors and your reason for the score. Suggest ways to improve.


            Question: {question}

            Ranking Guidelines:
            0: The answer is incorrect.
            1: The answer is partially correct but shows a significant misunderstanding.
            2: The answer includes some relevant points but missing the fully correct answer.
            3: The answer is mostly correct, but there are minor errors or omissions.
            4: The answer demonstrates a good understanding but could be more comprehensive.
            5: The answer is accurate and brought to the point.
            
            Please use following examples for your ranking:
            Examples: {student_data}	

            Evaluate the following student answers:
            Student Answer: {student_answer}

            Answer in this format please:
            Score:
            Feedback: """

            print(prompt)
            
            # API call
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages= [{"role" : "user", "content" : prompt}] ,
                max_tokens=10000,
                temperature=0.3
                )

            response = completion.choices[0].message['content']
            print("Response:", response)

            # Extract the score from the response
            result = response.split("\n")
            print("Result:", result)
            score = result[0].split(": ")[1]
            feedback = result[1].split(": ")[1]

            scores.append(score)
            feedbacks.append(feedback)

            print("Request:")
            print("Prompt:", prompt)
            print("Response:")
            print("Score:", score)
            print("Feedback:", feedback)
            print("-------------------------")

         # Return scores and feedbacks as JSON response
        return jsonify({'scores': scores, 'feedbacks': feedbacks})
    
    except Exception as e:
        print('Error scoring student answers:', e)
        return jsonify({'error': 'An error occurred while scoring student answers.'}), 500

# Run the Flask app if this script is executed
if __name__ == '__main__':
    app.run(debug=True)
