# -*- coding: utf-8 -*-
"""10x-React-Engineer.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/10Rr7ucLdPyMhQ3lmfNtdreHV-NTMIjQB
"""

import locale
locale.getpreferredencoding = lambda: "UTF-8"

!pip install -U accelerate

!pip install transformers

CodeWriterPrompt = """
<s>[INST] <<SYS>>

You will get instructions for react.js code to write.
You will write a very long answer. Make sure that every detail of the architecture is, in the end, implemented as code.

Think step by step and reason yourself to the right decisions to make sure we get it right.
You will first lay out the names of the core classes, functions, methods that will be necessary, as well as a quick comment on their purpose.

Then you will output the content of each file including ALL code.
Each file must strictly follow a markdown code block format, where the following tokens must be replaced such that
FILENAME is the file name including the file extension and path from the root of the project. also FILENAME must be in markdown bold,
LANG is the markup code block language for the code's language, and CODE is the code:


**FILENAME**
```LANG
CODE
```

Do not comment on what every file does

You will start with the entrypoint file which will must be called "index.js", then go to the ones that are imported by that file, and so on.
Please note that the code should be fully functional. No placeholders.
This will be a react.js project so you must create a webpack.config.js at the root of the project that uses "index.js" as the entry file
The output in the webpack.config.js must point to a bundle.js file that's in the same folder as the index.html
Place all of the public assets in a folder named "public" in lowercase with an index.html file that is linked to the bundle specified in the webpack.config.js
You must include a package.json file in the root of the folder that resolves all the required dependencies for this react.js project. All of the dependencies should be set to a * for the most up to date version.
The package.json must be valid JSON


Follow a language and framework appropriate best practice file naming convention.
Make sure that files contain all imports. Make sure that the code in different files are compatible with each other.
Ensure to implement all code, if you are unsure, write a plausible implementation.
Before you finish, double check that all parts of the architecture is present in the files.

Respond only with the output in the exact format specified in the system prompt, with no explanation or conversation.
<</SYS>>
"""

SummarizeAskPrompt = """
  You are an intelligent AI agent that understands the root of the users problems.

  The user will give an instruction for what code project they want to build.

  You will label what the users code project is in a short phrase no more than 3 words.

  Structure your label like this

  Label: enter the label here
"""

DependenciesPrompt = """
Your task is to look at a React.js Codebase and figure out what npm packages are missing so this codebase can run without any errors with webpack

The codebase will be a series of filenames and their source code. They will have the following format
FILENAME: the name of the file
SOURCE: the react component code

You will list each missing npm package in a markdown list format

Then you will return a newly updated package.json, with the new dependencies merged into the user's package.json dependencies. You will return it in the format below
PACKAGEJSON
```
the new package.json here
```

Respond only with the output in the exact format specified in the system prompt, with no explanation or conversation.
"""

ModificationPrompt = """
Your task is to take a user's react.js file and transform it based on the user's modification ask

The code must have the same imports as before and have the same variable names and the same export as before. ONLY modify the code based on the modification ask

If this file is not a react component do NOT make any modifications and return the code in same exact state that the user gave it to you

The user's code and their modification ask will be formatted like htis
CODE: the user's code
MODIFICATION: the user's modification

You will return the modified code in markdown format under the variable RETURNEDCODE. Follow the example below

RETURNEDCODE
```
the modified code here
```

Respond only with the output in the exact format specified in the system prompt, with no explanation or conversation.
"""

!huggingface-cli login

from transformers import AutoTokenizer
import transformers
import torch


# model = "meta-llama/Llama-2-13b-chat-hf"
model = "meta-llama/Llama-2-70b-chat-hf"

tokenizer = AutoTokenizer.from_pretrained(model)
pipeline = transformers.pipeline(
    "text-generation",
    model=model,
    torch_dtype=torch.float16,
    device_map="auto",
)

"""
  How our 10x React Engineer will code
  - We need to ask the user what
    - What is the design library?
  - We need to figure out if we need to build the backend
    - Load an express app in a single file
  - After we render
"""
import os
import re

def get_code_writer_prompt(code_prompt):
  return CodeWriterPrompt + "\nInstructions for the code: I want the entrypoint file for a "+code_prompt+" built in react.js [/INST]"

def get_summarization_prompt(user_ask):
  return SummarizeAskPrompt + "\nInstructions for the code project: "+user_ask+"  [/INST]"

def get_dependency_prompt(codebase):
  return DependenciesPrompt + "Using the codebase below determine whether this project is missing npm packages \n "+codebase+"  [/INST]"

def get_modification_prompt(code_block, modification_ask):
  return ModificationPrompt + "CODE:"+code_block+"\nMODIFICATION: "+modification_ask+"  [/INST]"

def generate(prompt):
  sequences = pipeline(
      prompt,
      do_sample=True,
      top_k=10,
      num_return_sequences=1,
      eos_token_id=tokenizer.eos_token_id,
      max_length=10000,
  )
  return sequences[0]['generated_text']

def parse_summarization_result(output):
  label_token = 'Label:'
  output_lines = output.split("\n")
  for i in reversed(range(0, len(output_lines))):
    if label_token in output_lines[i]:
      return output_lines[i][len(label_token):].strip()

def parse_scaffolding_result(output):
  output = output[output.index("[/INST]"):]
  code_blocks = re.findall(r"```(.*?)```", output, re.DOTALL)
  file_names = re.findall(r"\*\*(.*?)\*\*", output, re.DOTALL)
  print(file_names)
  print(code_blocks)
  code_files = []
  print("files length", len(file_names))
  print("codes length", len(code_blocks))

  for i in range(0, len(file_names)):
    if i < len(code_blocks):
      code_files.append({
          "file_name": file_names[i],
          "code_block": code_blocks[i]
      })

  return code_files

def initiate_code_modification(code_files, modification_ask):
  new_code_files = []
  for file_code_pair in code_files:
    mod_prompt = get_modification_prompt("\n".join(file_code_pair["code_block"].split("\n")[1:]), modification_ask)
    modification_result = generate(mod_prompt)
    print("MOD_RESULT:", modification_result)
    if "RETURNEDCODE" in modification_result:
      modification_result = modification_result[modification_result.index("[/INST]"):]
      code_block_raw_string = modification_result[modification_result.index("RETURNEDCODE") + len("RETURNEDCODE"):]
      file_code_pair["code_block"] = re.findall(r"```(.*?)```", code_block_raw_string, re.DOTALL)[0]
    new_code_files.append(file_code_pair)
  return new_code_files


def resolve_missing_dependencies(code_files):
  print("Resolving missing dependencies...")
  codebase = "\n".join(
    list(map(lambda x: f"FILENAME: {x['file_name']}\nSOURCE: {x['code_block']}\n", code_files))
  )
  dep_prompt = get_dependency_prompt(codebase)
  dep_result = generate(dep_prompt)
  dep_result = dep_result[dep_result.index("[/INST]"):]
  print(dep_result)
  if "PACKAGEJSON" in dep_result:
    package_json_text = re.findall(r"```(.*?)```", dep_result, re.DOTALL)[0]
    return package_json_text
  else:
    return None

def dev_loop(code_files, user_ask, modification_ask=None):
  if modification_ask:
    # update each related code block with a prediction using the modification ask of the user
    code_files = initiate_code_modification(code_files, modification_ask)

  # dependency resolving
  new_package_json = resolve_missing_dependencies(code_files)
  # set new package.json if it exists
  if new_package_json:
    for code_file in code_files:
      if 'package.json' in code_file["file_name"]:
        code_file["code_block"] = new_package_json

  for file_code_pair in code_files:
    filepath = "react-output/"+file_code_pair["file_name"]
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w+") as f:
      code_block = file_code_pair["code_block"].split("\n")[1:]
      f.write("\n".join(code_block).encode('ascii', 'ignore').decode('ascii'))

  print("Done! Check out your codebase in react-output/")
  user_input = input("$ Do you wish to make modifications? [y/n]")
  if user_input == "y":
    modification_ask = input("$ What modifications do you want to make?")
    dev_loop(code_files, user_ask, modification_ask=modification_ask)
  else:
    print("Congrats on your 10x React project")

def main():
  print("$ I am your personal 10x React Engineer ask me what you want to build?")
  init_user_ask = input("$ ")
  initial_sum_prompt = get_summarization_prompt(init_user_ask)
  summarization_result = generate(initial_sum_prompt)
  # print(summarization_result)
  project_summary = parse_summarization_result(summarization_result)
  print("Parsed Summary:", project_summary)
  print("\n\nBeginning scaffolding...\n\n")
  scaffolding_output = get_code_writer_prompt(project_summary)
  scaffolding_result = generate(scaffolding_output)
  print(scaffolding_result)
  code_files = parse_scaffolding_result(scaffolding_result)

  dev_loop(code_files, init_user_ask)
  # print("\n\nTask formulation...\n\n")
  # dev_loop(scaffolding_result, init_user_ask)
  # scaffold first
  # then design
  # and then add API functionality
# I want a calendar app with a nodejs backend
main()

# TODO
# - main thing is to fine tune 13b llama to be better at react
# - JSON fixer for package.json
# - add generated codebase as context to modification inferences
# - add option to modify everything vs file by file
# - make summarization optional

!zip -r react-output.zip react-output

!rm -rf react-output react-output.zip