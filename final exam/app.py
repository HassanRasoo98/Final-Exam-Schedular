from flask import Flask, render_template, request
import Levenshtein
import pandas as pd
import os

app = Flask(__name__)

# helper function to map user selected subject to the one in the original excel file
# to avoid issues
def get_most_similar_target(source, target_list):
    _, most_similar_target_index = max(
        ((Levenshtein.ratio(source, target), index) for index, target in enumerate(target_list)),
        key=lambda x: x[0]  # Use the similarity ratio as the key for max
    )
    most_similar_target = target_list[most_similar_target_index]
    return most_similar_target

# this one does the same thing but with more computational complexity according to gpt
# def get_most_similar_target(source, target_list):
#     similarities = [Levenshtein.ratio(source, target) for target in target_list]
#     max_similarity_index = similarities.index(max(similarities))
#     most_similar_target = target_list[max_similarity_index]
#     return most_similar_target

# Function to read subjects from the text file
def read_subjects():
    file_path = os.path.join(os.path.dirname(__file__), "all subjects.txt")

    try:
        with open(file_path, "r") as file:
            subjects = file.read().splitlines()
        return subjects
    except FileNotFoundError:
        print('file not found')
        return []
    
# load dataframe from excel file and return all subject list
def load_df():
    df = pd.ExcelFile("Final  Exams Schedule Fall 2023  Ver-Final   as on 11-12-2023.xlsx")
    df = df.parse('FSC Final')
    df.head()
    
    df.columns = df.iloc[3]
    df.drop([0, 1, 2, 3], axis=0, inplace=True)
    df = df.reset_index(drop=True)
    df.ffill(inplace=True)
    df.dropna(axis=1, inplace=True)
    df.head()
    
    # Remove every row after the 164th index
    df = df.drop(df.index[161:])

    # Resetting the index after removal
    df = df.reset_index(drop=True)
    df.index[160:]
    
    df['Days & Date'] = pd.to_datetime(df['Days & Date'])
    subjects = list(df['9:00 to 12:00 PM'].unique()) + list(df['1:00 to 4:00 PM'].unique()) + list(df['5:20 to 8:20 PM'].unique())
    return df, subjects
    
# Function to perform processing on the subject list
# refer to the final schedule ipynb jupyter file to understand the processing of this function
# the actual logic was made there and copy pasted here
def process_subjects(selected_subjects):
    inverse_map = []
    df, subjects = load_df()

    for subject in selected_subjects:
        most_similar_target = get_most_similar_target(subject, subjects)
        inverse_map.append(most_similar_target)
        
    # Your existing code for filtering and creating the final_df
    filtered_df = df[df.apply(lambda row: any(val in row.values for val in inverse_map), axis=1)]
    df_no_duplicates = filtered_df.drop_duplicates()
    df_no_duplicates.reset_index(drop=True, inplace=True)

    def get_matching_columns(row):
        return list(df_no_duplicates.columns[row.isin(inverse_map)])[0]

    df_no_duplicates['matching_columns'] = df_no_duplicates.apply(get_matching_columns, axis=1)
    df_no_duplicates.reset_index(drop=True, inplace=True)

    final_df = pd.DataFrame(columns=['Subject', 'Days & Date', 'Time'])

    for i, j in df_no_duplicates.iterrows():
        time = df_no_duplicates['matching_columns'].iloc[i]
        final_df.at[i, 'Subject'] = df_no_duplicates[str(time)].iloc[i]
        final_df.at[i, 'Time'] = time
        final_df.at[i, 'Days & Date'] = df_no_duplicates['Days & Date'].iloc[i]

    # Sorting the DataFrame based on the 'Days & Date' column
    final_df.sort_values(by='Days & Date', inplace=True)

    # Additional processing (e.g., formatting dates, etc.)
    final_df['Date'] = pd.to_datetime(final_df['Days & Date'])
    final_df['Days & Date'] = final_df['Days & Date'].apply(lambda date: date.strftime('%d-%m-%Y'))
    final_df['Day_Name'] = final_df['Date'].apply(lambda date: date.day_name())
    final_df = final_df[['Subject', 'Day_Name', 'Days & Date', 'Time']]
    
    final_df = final_df.drop_duplicates()
    
    # change the timings of Friday exam
    condition = (final_df['Time'] == '1:00 to 4:00 PM') & (final_df['Day_Name'] == 'Friday')
    column_to_modify = 'Time'
    new_value = '1:30 to 4:30 PM'

    final_df.loc[condition, column_to_modify] = new_value

    # Convert the final DataFrame to a list of dictionaries
    result_list = final_df.to_dict(orient='records')

    return result_list

# New route to handle processing and display result
@app.route("/process", methods=["POST"])
def process_selected_subjects():
    if request.method == "POST":
        selected_subjects = request.form.getlist("selected_subjects")
        processed_result = process_subjects(selected_subjects)
        print('processing')
        return render_template("selected_subjects.html", processed_result=processed_result)


# Route to display the form and subject list
@app.route("/", methods=["GET", "POST"])
def select_subjects():
    if request.method == "POST":
        selected_subjects = request.form.getlist("selected_subjects")
        return render_template("selected_subjects.html", selected_subjects=selected_subjects)

    subjects = read_subjects()
    
    # inverse map selected subjects to those found in the original excel file
    inverse_map = []

    for subject in subjects:
        most_similar_target = get_most_similar_target(subject, subjects)
        inverse_map.append(most_similar_target)
        
    return render_template("select_subjects.html", subjects=inverse_map)

if __name__ == "__main__":
    app.run(debug=True)
