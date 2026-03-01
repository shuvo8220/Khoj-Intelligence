import warnings
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# Suppress warnings
warnings.filterwarnings("ignore")

class TextSummarizer:
    """
    True AI Summarizer using Direct Model Loading.
    Optimized for LONGER and DETAILED summaries.
    """
    def __init__(self):
        self.tokenizer = None
        self.model = None
        self.use_ai = False
        
        try:
            print(" Loading AI Brain (Model)...")
            
            # Using the same robust model
            model_name = "sshleifer/distilbart-cnn-12-6"
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            
            self.use_ai = True
            print(" AI Model Ready! Detailed summaries enabled.")
            
        except Exception as e:
            print(f" AI Engine Failed: {e}")
            self.use_ai = False

    def summarize(self, text):
        """
        Generates a detailed abstractive summary.
        """
        if not text: return "No content."
        
        # Fallback
        if not self.use_ai:
            return "AI Model missing."

        try:
            # 1. Input Limit: Increased to 5000 characters to read more context
            input_text = text[:5000] 

            inputs = self.tokenizer(
                input_text, 
                max_length=1024, 
                truncation=True, 
                return_tensors="pt"
            )

            # 2. Generate Detailed Summary
            # Changed parameters for longer output
            summary_ids = self.model.generate(
                inputs["input_ids"], 
                num_beams=4, 
                
                # --- KEY CHANGES HERE ---
                max_length=400,   
                min_length=120,   
                length_penalty=2.0, 
                early_stopping=True
            )
            
            # 3. Decode
            summary_text = self.tokenizer.decode(
                summary_ids[0], 
                skip_special_tokens=True, 
                clean_up_tokenization_spaces=True
            )
            
            return summary_text
            
        except Exception as e:
            print(f"Summarization Error: {e}")
            return "Could not generate summary."