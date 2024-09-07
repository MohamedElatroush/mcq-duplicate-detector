import tkinter as tk
import customtkinter
from tkinter import filedialog
import os
from docx import Document
import fitz  # PyMuPDF
import re
from lxml import etree
import pdfplumber
from collections import defaultdict
import threading
import time  # Used to simulate progress for the progress bar

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")


def is_question_number(text):
    return re.match(r'^\d{1,3}\.\s', text) is not None


def read_pdf_file(filename, progress_callback):
    question_dict = {}
    current_question_num = None
    current_question_text = ''
    previous_lines = []

    with pdfplumber.open(filename) as pdf:
        total_pages = len(pdf.pages)
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text:
                lines = text.split("\n")
                lines = previous_lines + lines
                
                for line in lines:
                    match = re.match(r'^(\d+)\.\s', line)
                    if match:
                        if current_question_num:
                            question_dict[current_question_num] = current_question_text.strip()
                        current_question_num = match.group(1)
                        current_question_text = line[len(match.group(0)):]
                    else:
                        current_question_text += ' ' + line
                
                previous_lines = lines[-len(lines):]
            
            # Update progress
            progress_callback(page_num / total_pages)
        
        if current_question_num:
            question_dict[current_question_num] = current_question_text.strip()
    
    return question_dict


def UploadButton(event=None):
    filename = filedialog.askopenfilename()
    if filename:
        file_name_only = os.path.basename(filename)
        title.configure(text=f"Processing... {file_name_only}", text_color="orange")
        progress_bar.set(0)  # Reset progress bar to 0%
        progress_bar.pack(padx=10, pady=10)  # Make the progress bar visible

        # Start a new thread to process the file to avoid freezing the UI
        threading.Thread(target=process_file, args=(filename, file_name_only)).start()


def process_file(filename, file_name_only):
    ext = os.path.splitext(filename)[1].lower()
    
    if ext == '.pdf':
        questions = read_pdf_file(filename, update_progress)
        duplicates = detect_duplicates(questions)
        
        if duplicates:
            output_file = ask_save_location(file_name_only)
            if output_file:  # If user didn't cancel the save dialog
                highlight_duplicates(filename, output_file, duplicates)
                title.configure(text=f"Selected: {file_name_only} ({len(questions)} questions). Duplicates highlighted.", text_color="green")
                display_duplicates(duplicates)
        else:
            title.configure(text=f"No duplicates found in {file_name_only}.", text_color="blue")
            duplicates_label.configure(text="")  # Clear label if no duplicates found
    else:
        title.configure(text="Invalid file format", text_color="red")

    # Final progress step to 100%
    progress_bar.set(1)
    title.configure(text=f"Selected: {file_name_only} processing complete", text_color="green")


def ask_save_location(default_filename):
    """
    Ask the user where to save the file, return the selected file path.
    """
    save_location = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf")],
        initialfile=f"highlighted_{default_filename}",
        title="Save the highlighted PDF"
    )
    return save_location


def highlight_duplicates(original_pdf_path, output_pdf_path, duplicates):
    doc = fitz.open(original_pdf_path)
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        for duplicate in duplicates:
            question_number = duplicate.split('.')[0] + '.'
            areas = page.search_for(question_number)
            for area in areas:
                highlight = page.add_highlight_annot(area)
                highlight.set_colors(stroke=(1, 0, 0))  # RGB for red color
                highlight.update()
    
    try:
        doc.save(output_pdf_path)
        print(f"Highlighted duplicates saved to: {output_pdf_path}")
    except Exception as e:
        print(f"Error saving highlighted PDF: {e}")
    finally:
        doc.close()
    
def detect_duplicates(question_dict):
    question_texts = defaultdict(list)
    
    for num, text in question_dict.items():
        question_texts[text].append(num)
    
    duplicates = {text: nums for text, nums in question_texts.items() if len(nums) > 1}
    
    return duplicates


def display_duplicates(duplicates):
    duplicate_text = ""
    for _, numbers in duplicates.items():
        duplicate_text += f"Duplicated question numbers: {', '.join(numbers)}\n"
    
    duplicates_label.configure(text=duplicate_text)


def update_progress(progress):
    """
    Update the progress bar. `progress` is a value between 0 and 1.
    """
    progress_bar.set(progress)


app = customtkinter.CTk()
app.geometry("720x480")
app.title("MCQ duplicate finder")

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

# Add a label to display duplicates
duplicates_label = customtkinter.CTkLabel(app, text="", justify="left")
duplicates_label.pack(padx=10, pady=10)

app.mainloop()