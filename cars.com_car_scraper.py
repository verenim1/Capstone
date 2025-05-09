import tkinter as tk
import traceback
from tkinter import ttk, messagebox, filedialog
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import csv
import threading
from queue import Queue
import webbrowser
import os
from geopy.geocoders import Nominatim 
#from dotenv import load_dotenv

# Load environment variables for Facebook credentials
#load_dotenv()

class RealCopartCarScraper:
    def __init__(self, root):
        self.root = root
        self.root.title("cars Marketplace Car Finder - Real Scraper")
        self.root.geometry("1000x800")
        
        # Configure Chrome options
        self.chrome_options = Options()
        self.chrome_options.add_argument("--disable-notifications")
        self.chrome_options.add_argument("--disable-infobars")
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--enable-unsafe-swiftshader")
        

        
        # Queue for thread-safe GUI updates
        self.queue = Queue()
        
        # Setup GUI
        self.setup_gui()
        
        # Check queue periodically
        self.root.after(100, self.process_queue)
    
    def setup_gui(self):
        """Set up the graphical user interface."""
        # Main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Search parameters frame
        self.search_frame = ttk.LabelFrame(self.main_frame, text="Search Parameters", padding="10")
        self.search_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Make
        ttk.Label(self.search_frame, text="Make (e.g., Toyota):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.make_entry = ttk.Entry(self.search_frame, width=30)
        self.make_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Model
        ttk.Label(self.search_frame, text="Model (e.g., Camry):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.model_entry = ttk.Entry(self.search_frame, width=30)
        self.model_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Min Year
        ttk.Label(self.search_frame, text="Min Year:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.min_year_entry = ttk.Entry(self.search_frame, width=10)
        self.min_year_entry.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        
        # Max Year
        ttk.Label(self.search_frame, text="Max Year:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.max_year_entry = ttk.Entry(self.search_frame, width=10)
        self.max_year_entry.grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)
        
        # Max Price
        ttk.Label(self.search_frame, text="Max Price ($):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.max_price_entry = ttk.Entry(self.search_frame, width=30)
        self.max_price_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Location
        ttk.Label(self.search_frame, text="Location (Zip Code):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.location_entry = ttk.Entry(self.search_frame, width=30)
        self.location_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Distance
        ttk.Label(self.search_frame, text="Distance (miles):").grid(row=3, column=2, sticky=tk.W, padx=5, pady=5)
        self.distance_combobox = ttk.Combobox(self.search_frame, values=["10", "20", "30", "40", "50", "100"], width=8)
        self.distance_combobox.set("20")
        self.distance_combobox.grid(row=3, column=3, sticky=tk.W, padx=5, pady=5)
        
        # Max Results
        ttk.Label(self.search_frame, text="Max Results:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=5)
        self.max_results_combobox = ttk.Combobox(self.search_frame, values=["10", "20", "30", "50", "100"], width=8)
        self.max_results_combobox.set("20")
        self.max_results_combobox.grid(row=2, column=3, sticky=tk.W, padx=5, pady=5)
        
        # Button frame
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.search_button = ttk.Button(self.button_frame, text="Search Marketplace", command=self.start_search_thread)
        self.search_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = ttk.Button(self.button_frame, text="Clear Results", command=self.clear_results)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        self.export_button = ttk.Button(self.button_frame, text="Export to CSV", command=self.export_to_csv)
        self.export_button.pack(side=tk.LEFT, padx=5)
        
        # Results frame
        self.results_frame = ttk.LabelFrame(self.main_frame, text="Search Results", padding="10")
        self.results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview for results
        self.tree = ttk.Treeview(self.results_frame, columns=("Price", "Title", "Year", "Location", "Miles", "Link"), show="headings")
        
        self.tree.heading("Price", text="Price", anchor=tk.W)
        self.tree.heading("Title", text="Title", anchor=tk.W)
        self.tree.heading("Year", text="Year", anchor=tk.W)
        self.tree.heading("Location", text="Location", anchor=tk.W)
        self.tree.heading("Miles", text="Miles", anchor=tk.W)
        self.tree.heading("Link", text="Link", anchor=tk.W)
        
        self.tree.column("Price", width=100, stretch=tk.NO)
        self.tree.column("Title", width=250, stretch=tk.YES)
        self.tree.column("Year", width=70, stretch=tk.NO)
        self.tree.column("Location", width=150, stretch=tk.NO)
        self.tree.column("Miles", width=100, stretch=tk.NO)
        self.tree.column("Link", width=100, stretch=tk.NO)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        self.scrollbar = ttk.Scrollbar(self.tree, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(self.main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X)
        
        # Bind double click to open link
        self.tree.bind("<Double-1>", self.open_link)
        
        # Sample data for testing (remove in production)
        self.make_entry.insert(0, "Toyota")
        self.model_entry.insert(0, "Camry")
        self.max_price_entry.insert(0, "15000")
        self.location_entry.insert(0, "13501")
        self.min_year_entry.insert(0, "2015")
        self.max_year_entry.insert(0, "2020")
    
    def start_search_thread(self):
        """Start the search in a separate thread to keep the GUI responsive."""
        if not self.validate_inputs():
            return
            
        # Disable buttons during search
        self.search_button.config(state=tk.DISABLED)
        self.clear_button.config(state=tk.DISABLED)
        self.export_button.config(state=tk.DISABLED)
        
        # Clear previous results
        self.clear_results()
        
        # Update status
        self.status_var.set("Initializing...")
        
        # Get search parameters
        make = self.make_entry.get().strip()
        model = self.model_entry.get().strip()
        min_year = self.min_year_entry.get().strip()
        max_year = self.max_year_entry.get().strip()
        max_price = self.max_price_entry.get().strip()
        location = self.location_entry.get().strip()
        distance = self.distance_combobox.get().strip()
        max_results = int(self.max_results_combobox.get().strip())
        
        # Start the search thread
        search_thread = threading.Thread(
            target=self.scrape_carsdotcom,
            args=(make, model, min_year, max_year, max_price, location, distance, max_results),
            daemon=True
        )
        search_thread.start()
    def load_car_list(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("Text Files", "*.txt")])
        if not file_path:
            return

        car_list = []
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                parts = line.strip().split(',')
                if len(parts) >= 2:
                    make, model = parts[0], parts[1]
                    car_list.append((make, model))

        self.start_batch_search(car_list)

    def start_batch_search(self, car_list):
        def batch_worker():
            for make, model in car_list:
                self.queue.put(("status", f"Searching: {make} {model}"))
                self.scrape_copart(
                    make, model,
                    self.min_year_entry.get().strip(),
                    self.max_year_entry.get().strip(),
                    self.max_price_entry.get().strip(),
                    self.location_entry.get().strip(),
                    self.distance_combobox.get().strip(),
                    int(self.max_results_combobox.get().strip())
                )
                time.sleep(2)  # Optional: small pause between searches
            self.queue.put(("enable_buttons", None))
        threading.Thread(target=batch_worker, daemon=True).start()


    def validate_inputs(self):
        """Validate user inputs before searching."""
        make = self.make_entry.get().strip()
        model = self.model_entry.get().strip()
        max_price = self.max_price_entry.get().strip()
        min_year = self.min_year_entry.get().strip()
        max_year = self.max_year_entry.get().strip()
        
        if not make:
            messagebox.showerror("Error", "Please enter a car make (e.g., Toyota)")
            return False
            
        if not model:
            messagebox.showerror("Error", "Please enter a car model (e.g., Camry)")
            return False
            
        if max_price and not max_price.isdigit():
            messagebox.showerror("Error", "Max price must be a number")
            return False
            
        if min_year and (not min_year.isdigit() or len(min_year) != 4):
            messagebox.showerror("Error", "Min year must be a 4-digit year")
            return False
            
        if max_year and (not max_year.isdigit() or len(max_year) != 4):
            messagebox.showerror("Error", "Max year must be a 4-digit year")
            return False
            
        return True
    
    def scrape_carsdotcom(self, make, model, min_year, max_year, max_price, location, distance, max_results):
        from urllib.parse import quote_plus
        driver = None
        try:
            self.queue.put(("status", "Setting up ChromeDriver..."))
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=self.chrome_options)
            driver.implicitly_wait(10)

            self.queue.put(("status", f"Searching Cars.com for {make} {model}..."))
            # Validate the zip code
            if not location.isdigit() or len(location) != 5:
                self.queue.put(("error", "Please enter a valid 5-digit zip code."))
                return
        
            # Construct search URL
            base_url = "https://www.cars.com/shopping/results/"
            query_params = f"?stock_type=used&makes[]={make.lower()}&models[]={make.lower()}-{model.lower()}" \
                            f"&list_price_max={max_price}&maximum_distance={distance}&zip={location}" \
                            f"&year_min={min_year}&year_max={max_year}&page=1&page_size=100"
            search_url = base_url + query_params
            driver.get(search_url)

            self.scroll_page(driver, max_results)

            listings = self.extract_carsdotcom_listings(driver, max_results)
            self.process_results(listings)

            self.queue.put(("status", f"Found {len(listings)} results. Ready"))
        except Exception as e:
            error_message = f"{str(e)}\n\n{traceback.format_exc()}"
            self.queue.put(("error", f"Error during scraping:\n{error_message}"))
            if driver:
                driver.save_screenshot("error_screenshot.png")
                self.queue.put(("status", "Error occurred. Screenshot saved as error_screenshot.png"))
        finally:
            input("Press enter to close the window...")
            if driver:
                driver.quit()
            self.queue.put(("enable_buttons", None))
        
        # Wait for login to complete
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(text(),'Marketplace')]"))
            )
        except:
            # Check for login error
            if "login_attempt" in driver.current_url:
                self.queue.put(("error", "copart login failed. Check credentials."))
                raise Exception("copart login failed")
    
    def scroll_page(self, driver, max_results):
        """Scroll the page to load more results."""
        last_height = driver.execute_script("return document.body.scrollHeight")
        loaded_results = 0
        
        while True:
            # Get current number of listings
            listings = driver.find_elements(By.XPATH, "//div[contains(@aria-label,'Collection of Marketplace items')]/div/div")
            loaded_results = len(listings)
            
            # Stop if we have enough results or can't scroll further
            if loaded_results >= max_results:  # Load extra to account for potential non-car listings
                break
                
            # Scroll down
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Wait for new content to load
            
            # Check if we've reached the bottom
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height


    def extract_numeric_miles(self, mileage_text):
        """Extract numeric miles from the mileage text."""
        import re
        miles_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*(?:mi|miles)', mileage_text, re.IGNORECASE)
        if miles_match:
            return int(miles_match.group(1).replace(',', ''))  # Convert to integer
        return 0 
    
    def extract_carsdotcom_listings(self, driver, max_results):
        listings = []
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        cards = soup.select('div.vehicle-card')
    
        for card in cards:
            if len(listings) >= max_results:
                break
            try:
                title = card.select_one('h2.title').get_text(strip=True)
                price = card.select_one('span.primary-price').get_text(strip=True)
                location = card.select_one('div.dealer-name').get_text(strip=True)
                mileage_text = card.select_one('div.mileage').get_text(strip=True) if card.select_one('div.mileage') else "N/A"
                link_tag = card.select_one('a.vehicle-card-link')
                link = "https://www.cars.com" + link_tag['href'] if link_tag else "N/A"
                year_match = self.extract_year_and_miles(title)[0]

                # Convert price and miles to numeric values
                numeric_price = int(price.replace('$', '').replace(',', '')) if price and price[0] == '$' else 0

                # Convert mileage to numeric value
                numeric_miles = self.extract_numeric_miles(mileage_text)

                listings.append({
                    'title': title,
                    'price': price,
                    'location': location,
                    'miles': mileage_text,
                    'year': year_match,
                    'link': link,
                    'numeric_price' : numeric_price,
                    'numeric_miles' : numeric_miles,
                })
            except Exception as e:
                print(f"[DEBUG] Skipping a listing due to error: {e}")
        return listings [:max_results]

    
    def extract_year_and_miles(self, title):
        """Extract year and mileage from the title string."""
        import re
        
        # Extract year (4-digit number between 1900-2100)
        year_match = re.search(r'(19|20)\d{2}', title)
        year = year_match.group(0) if year_match else "N/A"
        
        # Extract mileage (numbers followed by "mi" or "miles")
        miles_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*(?:mi|miles)', title, re.IGNORECASE)
        miles = miles_match.group(1) + " miles" if miles_match else "N/A"
        
        return year, miles
    
    def process_results(self, results):
        """Process the scraped results and add them to the Treeview."""
        if not results:
            self.queue.put(("status", "No results found. Try different search parameters."))
            return
        print(f"[DEBUG] Processing {len(results)} results")  # Debug statement
        
        #sorts by price
        results.sort(key=lambda x: x["numeric_price"] / max(1, x["numeric_miles"]))

        # Add to treeview
        for result in results:
            self.queue.put(("add_result", (result, False)))  # Assuming False for is_best for simplicity
            
        # Sort by price per mile (best value)
        results.sort(key=lambda x: x["numeric_price"] / max(1, x["numeric_miles"]))
        
        # Add to treeview
        for i, result in enumerate(results):
            is_best = i == 0  # First result is best deal
            self.queue.put(("add_result", (result, is_best)))
    
    def add_result_to_treeview(self, result, is_best):
        """Add a single result to the Treeview."""
        tags = ("best",) if is_best else ()
        
        self.tree.insert("", tk.END, 
                        values=(result["price"], result["title"], result["year"], 
                                result["location"], result["miles"], result["link"]), 
                        tags=tags)
        
        if is_best:
            self.tree.tag_configure("best", background="#e6f7ff")  # Light blue for best deal
    
    def clear_results(self):
        """Clear all results from the Treeview."""
        self.tree.delete(*self.tree.get_children())
        self.status_var.set("Ready")
    
    def open_link(self, event):
        """Open the selected listing in a web browser."""
        selected_item = self.tree.focus()
        if not selected_item:
            return
            
        item_data = self.tree.item(selected_item)
        link = item_data["values"][5]  # Link is the 6th column
        
        if link and link != "N/A":
            webbrowser.open(link)
    
    def export_to_csv(self):
        """Export the search results to a CSV file."""
        try:
            # Ask for file location
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
                title="Save Results As"
            )
            
            if not file_path:
                return
                
            # Get all items from the Treeview
            items = self.tree.get_children()
            
            if not items:
                messagebox.showwarning("No Data", "No results to export")
                return
                
            # Write to CSV
            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                
                # Write headers
                headers = [self.tree.heading(col)["text"] for col in self.tree["columns"]]
                writer.writerow(headers)
                
                # Write data
                for item in items:
                    row = self.tree.item(item)["values"]
                    writer.writerow(row)
                    
            self.status_var.set(f"Results exported to {file_path}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export results: {str(e)}")
    
    def process_queue(self):
        """Process messages from the queue to update the GUI thread-safely."""
        while not self.queue.empty():
            try:
                message = self.queue.get_nowait()
                
                if message[0] == "status":
                    self.status_var.set(message[1])
                elif message[0] == "error":
                    messagebox.showerror("Error", message[1])
                elif message[0] == "add_result":
                    self.add_result_to_treeview(message[1][0], message[1][1])
                elif message[0] == "enable_buttons":
                    self.search_button.config(state=tk.NORMAL)
                    self.clear_button.config(state=tk.NORMAL)
                    self.export_button.config(state=tk.NORMAL)
                    
            except Exception as e:
                print(f"Error processing queue message: {e}")
                
        self.root.after(100, self.process_queue)

if __name__ == "__main__":
    root = tk.Tk()  # Create a Tkinter root window
    app = RealCopartCarScraper(root)  # Pass the root window to the scraper
    root.mainloop()  # Start the Tkinter event loop
