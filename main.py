import customtkinter
from tkinter.filedialog import askopenfilename, asksaveasfilename
import fitz  # PyMuPDF for extracting text
import difflib
import re
import random
import os
import threading

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")

# Initialize the application
app = customtkinter.CTk()
app.geometry("720x480")
app.title("MCQ Duplicate Finder")

# Function to extract text from a PDF
def extract_text_from_pdf(pdf_file):
    doc = fitz.open(pdf_file)
    text = ""
    for page in doc:
        text += page.get_text()
    return text, doc

# Function to extract questions (split based on numbering or option patterns)
def extract_mcq_questions(text):
    questions = []
    pattern = re.compile(r'\n\d+\.\s+|\n[a-zA-Z]\)\s+')
    parts = pattern.split(text)
    
    for part in parts:
        if part.strip():
            questions.append(part.strip())
    
    return questions

# Function to find groups of similar questions using difflib
def find_similar_questions(questions, threshold=0.9):
    similar_groups = []
    n = len(questions)
    used = set()  # To track questions that are already grouped

    for i in range(n):
        if i in used:
            continue  # Skip if this question is already in a group
        group = [questions[i]]  # Start a new group
        for j in range(i + 1, n):
            if j in used:
                continue
            ratio = difflib.SequenceMatcher(None, questions[i], questions[j]).ratio()
            if ratio >= threshold:
                group.append(questions[j])
                used.add(j)
        if len(group) > 1:  # Only add groups with more than one similar question
            similar_groups.append(group)
    return similar_groups

# Function to highlight duplicate paragraphs in PDF
def highlight_paragraphs(doc, similar_questions):
    colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, 0, 1), (0, 1, 1)]  # RGB colors
    used_colors = []  # To track used colors and avoid reusing them
    
    for group in similar_questions:
        # Select a new unique color for the group
        available_colors = [color for color in colors if color not in used_colors]
        if available_colors:
            color = random.choice(available_colors)  # Choose a random available color
            used_colors.append(color)  # Mark color as used
        else:
            color = random.choice(colors)  # If all colors used, start reusing

        # Loop through each question in the group
        for question in group:
            # Loop through each page to search for the question
            for page in doc:
                text_instances = page.search_for(question)  # Search for all exact occurrences
                # Highlight all instances found on the page
                for inst in text_instances:
                    highlight = page.add_highlight_annot(inst)  # Add highlight annotation for each instance
                    highlight.set_colors(stroke=color)  # Set the highlight color for the group
                    highlight.update()  # Apply the changes

def ask_save_location(default_filename):
    """
    Ask the user where to save the file, return the selected file path.
    """
    save_location = asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf")],
        initialfile=f"highlighted_{default_filename}",
        title="Save the highlighted PDF"
    )
    return save_location

def process_pdf(pdf_file):
    try:
        # Extract text from the uploaded PDF
        text, doc = extract_text_from_pdf(pdf_file)
        update_progress(0.3)

        # Extract questions and find similar ones
        questions = extract_mcq_questions(text)
        similar_questions = find_similar_questions(questions)
        update_progress(0.6)

        # Highlight similar questions
        if similar_questions:
            highlight_paragraphs(doc, similar_questions)
            update_progress(1.0)  # Set progress bar to 100%
            progress_bar.pack_forget()  # Hide progress bar once done
            # Ask user for save location after processing is complete
            save_path = ask_save_location("Highlighted_Similar_Questions.pdf")
            if save_path:
                doc.save(save_path)  # Save the new PDF with highlights
                result_text = f"Similar questions highlighted. New file saved as '{save_path}'"
            else:
                result_text = "File saving canceled"
        else:
            result_text = "No similar questions found"
        
        update_progress(1.0)  # Set progress bar to 100%
    finally:
        doc.close()  # Close the PDF
        # Re-enable the button and reset the text after processing is done
        button.configure(text="Open", state="normal")
        progress_bar.pack_forget()  # Hide progress bar once done
        duplicates_label.configure(text=result_text)
        app.update()  # Ensure the GUI updates to reflect the changes

def UploadButton():
    pdf_file = askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if pdf_file:
        # Disable the button and change the text to indicate loading
        button.configure(text="Processing...", state="disabled")
        progress_bar.pack(pady=10)  # Show progress bar
        progress_bar.set(0)  # Initialize progress bar to 0
        app.update()  # Update the GUI to show the progress bar immediately
        
        # Run the PDF processing in a separate thread
        threading.Thread(target=process_pdf, args=(pdf_file,)).start()

def update_progress(value):
    """
    Update the progress bar from the main thread.
    """
    progress_bar.set(value)
    app.update()
    
# Add program name label with larger text
program_name_label = customtkinter.CTkLabel(app, text="MCQ Duplicate Finder", font=("Arial", 24, "bold"))
program_name_label.pack(pady=20)

# Add title label
title = customtkinter.CTkLabel(app, text="Upload file")
title.pack(padx=10, pady=10)

# Add upload button
button = customtkinter.CTkButton(app, text='Open', command=UploadButton)
button.pack(pady=10)

# Add progress bar (hidden initially)
progress_bar = customtkinter.CTkProgressBar(app, width=500)
progress_bar.set(0)  # Initialize the progress bar to 0
progress_bar.pack_forget()  # Hide progress bar initially

# Add a label to display results
duplicates_label = customtkinter.CTkLabel(app, text="", justify="left")
duplicates_label.pack(padx=10, pady=10)

app.mainloop()