from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
import time

def setupFirefoxDriver():
    # Use the same profile path that worked for Squarespace
    profilePath = r"C:\Users\Grant\AppData\Roaming\Mozilla\Firefox\Profiles\gtcaey7c.automation"
    profile = webdriver.FirefoxProfile(profilePath)
    
    # Set Firefox binary location
    firefoxOptions = Options()
    firefoxOptions.binary_location = r"C:\Program Files\Mozilla Firefox\firefox.exe"
    
    driver = webdriver.Firefox(firefox_profile=profile, options=firefoxOptions)
    return driver

# Create a single shared driver instance for all functions
driver = setupFirefoxDriver()

def fixStuckSonarrQueue():
    # Store the original URL to return to if needed
    originalUrl = "http://truenas.local:30113/activity/queue"
    
    try:
        # Navigate to Sonarr activity queue
        print("Opening Sonarr activity queue...")
        driver.get(originalUrl)
        
        # Wait for page to load - look for Series header
        print("Waiting for page to load...")
        wait = WebDriverWait(driver, 30)
        seriesHeader = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'th[label="Series"]')))
        print("Page loaded successfully!")
        
        # One-time: click the Status column header to sort by status
        try:
            print("Clicking Status column header once...")
            statusHeader = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'th[title="Status"]')))
            driver.execute_script("arguments[0].click();", statusHeader)
            time.sleep(0.5)
            print("Status column header clicked!")
        except Exception as e:
            print(f"Could not click Status header: {e}")
        
        # Function to check if we're on the correct page and return if needed
        def ensureCorrectPage():
            currentUrl = driver.current_url
            if originalUrl not in currentUrl:
                print(f"Not on Sonarr queue page (current: {currentUrl}), returning...")
                driver.get(originalUrl)
                time.sleep(3)
                # Wait for page to load again
                seriesHeader = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'th[label="Series"]')))
                print("Returned to Sonarr queue page")
                return True
            return False
        
        # Function to get user buttons with their row context
        def getUserButtons():
            # First ensure we're on the correct page
            ensureCorrectPage()
            
            userButtons = driver.find_elements(By.CSS_SELECTOR, 'button[aria-label="Table Options Button"] svg[data-icon="user"]')
            print(f"Found {len(userButtons)} user icon buttons")
            
            tableButtons = []
            for userIcon in userButtons:
                parentButton = userIcon.find_element(By.XPATH, './ancestor::button')
                buttonId = parentButton.get_attribute('id')
                print(f"User button ID: {buttonId}")
                
                # Skip sidebar toggle buttons
                if buttonId and 'sidebar' in buttonId.lower():
                    print(f"Skipping sidebar button: {buttonId}")
                    continue
                
                # Get the row containing this button to create a unique identifier
                try:
                    row = parentButton.find_element(By.XPATH, './ancestor::tr')
                    # Try to get series name from the row for better identification
                    seriesCell = row.find_element(By.CSS_SELECTOR, 'td[data-label="Series"]')
                    seriesName = seriesCell.text.strip() if seriesCell.text else "Unknown"
                    buttonIdentifier = f"{seriesName}_{buttonId}"
                except:
                    # Fallback to just the button ID if we can't get series name
                    buttonIdentifier = buttonId or f"button_{len(tableButtons)}"
                
                tableButtons.append((parentButton, buttonIdentifier))
            
            return tableButtons
        
        # Keep track of processed buttons to avoid duplicates
        processedButtons = set()
        buttonCount = 0
        noButtonsFirstTime = True
        
        while True:
            # Ensure we're on the correct page before processing
            ensureCorrectPage()
            
            # Get current user buttons
            tableButtons = getUserButtons()
            
            if not tableButtons:
                if noButtonsFirstTime:
                    print("No user buttons found. Checking if we're on the correct page...")
                    ensureCorrectPage()
                    
                    # Try getting buttons again after ensuring correct page
                    tableButtons = getUserButtons()
                    if tableButtons:
                        print(f"Found {len(tableButtons)} buttons after returning to correct page")
                        continue
                    
                    print("Still no user buttons found. Waiting 15 seconds then refreshing...")
                    time.sleep(15)
                    
                    print("Clicking refresh button...")
                    try:
                        refreshButton = driver.find_element(By.CSS_SELECTOR, 'button.PageToolbarButton-toolbarButton-j8a_b svg[data-icon="arrows-rotate"]')
                        parentRefreshButton = refreshButton.find_element(By.XPATH, './ancestor::button')
                        driver.execute_script("arguments[0].click();", parentRefreshButton)
                        print("Refresh button clicked!")
                        time.sleep(3)
                    except Exception as e:
                        print(f"Could not click refresh button: {e}")
                    
                    print("Refreshing page...")
                    driver.refresh()
                    time.sleep(5)
                    
                    # Wait for page to load - look for Series header again
                    print("Waiting for page to reload...")
                    seriesHeader = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'th[label="Series"]')))
                    print("Page reloaded successfully!")
                    time.sleep(2)
                    
                    # Reset processed buttons since page refreshed
                    processedButtons = set()
                    noButtonsFirstTime = False
                    continue
                else:
                    print("No more user buttons found after refresh - ending")
                    break
            
            # Reset flag since we found buttons
            noButtonsFirstTime = True
            
            print(f"Found {len(tableButtons)} user buttons")
            
            # Find the first unprocessed button
            currentButton = None
            currentIdentifier = None
            for i, (userButton, buttonIdentifier) in enumerate(tableButtons):
                if buttonIdentifier not in processedButtons:
                    currentButton = userButton
                    currentIdentifier = buttonIdentifier
                    processedButtons.add(buttonIdentifier)
                    print(f"Processing button {i+1} of {len(tableButtons)} (ID: {buttonIdentifier})")
                    break
            
            if not currentButton:
                print("No new buttons to process")
                # Wait a bit and check again in case buttons are still loading
                time.sleep(2)
                tableButtons = getUserButtons()
                if not tableButtons:
                    print("Still no buttons found after waiting - ending")
                    break
                else:
                    print(f"Found {len(tableButtons)} buttons after waiting, continuing...")
                    continue
            
            buttonCount += 1
            print(f"\n--- Processing user button {buttonCount} ---")
            
            # Click the current user button
            print(f"Clicking user button for: {currentIdentifier}")
            driver.execute_script("arguments[0].click();", currentButton)
            print("Button clicked successfully!")
            time.sleep(0.5)
            
            # Try to find and click the Import button with timeout
            try:
                print("Looking for Import button...")
                # Use a shorter timeout for Import button
                importWait = WebDriverWait(driver, 1)
                importButton = importWait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.Button-success-MO1fp')))
                print("Found Import button, clicking...")
                driver.execute_script("arguments[0].click();", importButton)
                print("Import button clicked successfully!")
                time.sleep(3)  # Wait 3 seconds after successful import
            except:
                print("Import button not found within 1 second, starting deletion process...")
                # Press Escape to return to main table
                from selenium.webdriver.common.keys import Keys
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(0.5)
                
                # Find the X icon in the same table row as the clicked user button
                try:
                    print("Looking for X icon in the same row...")
                    # Get the table row containing the clicked user button
                    userButtonRow = currentButton.find_element(By.XPATH, './ancestor::tr')
                    
                    # Find the X button within the same row
                    xButton = userButtonRow.find_element(By.CSS_SELECTOR, 'button[aria-label="Table Options Button"] svg[data-icon="xmark"]')
                    parentXButton = xButton.find_element(By.XPATH, './ancestor::button')
                    print("Found X button in same row, clicking...")
                    driver.execute_script("arguments[0].click();", parentXButton)
                    print("X button clicked successfully!")
                    time.sleep(0.5)
                    
                    # Click the dropdown to select blocklist option
                    print("Clicking dropdown...")
                    time.sleep(0.5)
                    # Find the dropdown that shows "Do not Blocklist"
                    dropdowns = driver.find_elements(By.CSS_SELECTOR, 'button.EnhancedSelectInput-enhancedSelect-U5iFw')
                    targetDropdown = None
                    for dropdown in dropdowns:
                        try:
                            valueText = dropdown.find_element(By.CSS_SELECTOR, 'div.HintedSelectInputSelectedValue-valueText-RqVEn')
                            if "Do not Blocklist" in valueText.text:
                                targetDropdown = dropdown
                                break
                        except:
                            continue
                    
                    if targetDropdown:
                        driver.execute_script("arguments[0].click();", targetDropdown)
                        time.sleep(0.5)
                        
                        # Select the "Blocklist and Search" option from the dropdown
                        print("Selecting 'Blocklist and Search' option...")
                        try:
                            # Wait for dropdown options to appear
                            dropdownWait = WebDriverWait(driver, 1)
                            dropdownOptions = dropdownWait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.EnhancedSelectInputOption-option-VZhzN')))
                            print(f"Found {len(dropdownOptions)} dropdown options")
                            
                            # Look for the option that contains "Blocklist and Search" text
                            blocklistOption = None
                            for option in dropdownOptions:
                                try:
                                    optionText = option.find_element(By.CSS_SELECTOR, 'div.HintedSelectInputOption-optionText-X0Jgb div')
                                    if "Blocklist and Search" in optionText.text:
                                        blocklistOption = option
                                        break
                                except:
                                    continue
                            
                            if blocklistOption:
                                driver.execute_script("arguments[0].click();", blocklistOption)
                                print("Blocklist and Search option selected successfully!")
                                time.sleep(1)
                            else:
                                print("Could not find 'Blocklist and Search' option")
                                
                        except Exception as e:
                            print(f"Could not select dropdown option: {e}")
                    else:
                        print("Could not find the correct dropdown, proceeding with default settings")
                    
                    # Click the Remove button (always try this regardless of dropdown success)
                    print("Clicking Remove button...")
                    removeButton = driver.find_element(By.CSS_SELECTOR, 'button.Button-danger-vthZW')
                    driver.execute_script("arguments[0].click();", removeButton)
                    print("Remove button clicked successfully!")
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"Could not complete deletion process: {e}")
                    # Refresh page as fallback
                    print("Refreshing page as fallback...")
                    print("Clicking refresh button...")
                    try:
                        refreshButton = driver.find_element(By.CSS_SELECTOR, 'button.PageToolbarButton-toolbarButton-j8a_b svg[data-icon="arrows-rotate"]')
                        parentRefreshButton = refreshButton.find_element(By.XPATH, './ancestor::button')
                        driver.execute_script("arguments[0].click();", parentRefreshButton)
                        print("Refresh button clicked!")
                        time.sleep(10)
                    except Exception as refreshError:
                        print(f"Could not click refresh button: {refreshError}")
                    
                    print("Refreshing page...")
                    driver.refresh()
                    time.sleep(3)
                    
                    # Wait for page to load - look for Series header again
                    print("Waiting for page to reload...")
                    seriesHeader = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'th[label="Series"]')))
                    print("Page reloaded successfully!")
                    
                    # Additional wait to ensure page is fully stable
                    time.sleep(2)
            
            # Refresh page after every 5 buttons to ensure we don't miss any
            if buttonCount % 5 == 0:
                print(f"\n--- Refreshing page after processing {buttonCount} buttons ---")
                print("Clicking refresh button...")
                try:
                    refreshButton = driver.find_element(By.CSS_SELECTOR, 'button.PageToolbarButton-toolbarButton-j8a_b svg[data-icon="arrows-rotate"]')
                    parentRefreshButton = refreshButton.find_element(By.XPATH, './ancestor::button')
                    driver.execute_script("arguments[0].click();", parentRefreshButton)
                    print("Refresh button clicked!")
                    time.sleep(3)
                except Exception as e:
                    print(f"Could not click refresh button: {e}")
                
                print("Refreshing page...")
                driver.refresh()
                time.sleep(5)  # Wait longer for page to reload
                
                # Wait for page to load - look for Series header again
                print("Waiting for page to reload...")
                seriesHeader = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'th[label="Series"]')))
                print("Page reloaded successfully!")
                
                # Additional wait to ensure page is fully stable
                time.sleep(2)
                
                # Reset processed buttons after refresh to catch any that might have been missed
                processedButtons = set()
        
        print(f"\n--- Completed processing all user buttons ---")
        print(f"Total buttons processed: {buttonCount}")
        print(f"Processed button IDs: {processedButtons}")
        
        # Ensure we're back on the Sonarr queue page for subsequent functions
        ensureCorrectPage()
            
        # Keep the browser open for a few seconds to see the result
        time.sleep(5)
        
    except Exception as e:
        print(f"An error occurred: {e}")
    

def radarrGetWanted():
    url = "http://truenas.local:30025/wanted/missing"
    
    # Use shared driver
    driver.get(url)
    
    # Wait for page
    wait = WebDriverWait(driver, 20)
    time.sleep(3)
    
    # Click "Search All"
    try:
        searchAllButton = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'button[title="Search All"].PageToolbarButton-toolbarButton-j8a_b')
            )
        )
        searchAllButton.click()
        
        time.sleep(1)
        
        # Click "Search" (red button)
        searchButton = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'button.Button-danger-vthZW')
            )
        )
        searchButton.click()
        
        time.sleep(5)
    except:
        print("Button not found, probably already pressed.")
    
    # Keep browser open for subsequent tasks


def sonarrGetWanted():
    url = "http://truenas.local:30113/wanted/missing"
    
    # Use shared driver
    driver.get(url)
    
    # Wait for page
    wait = WebDriverWait(driver, 20)
    time.sleep(3)
    
    # Click "Search All"
    try:
        searchAllButton = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'button[title="Search All"].PageToolbarButton-toolbarButton-j8a_b')
            )
        )
        searchAllButton.click()
        
        time.sleep(1)
        
        # Click "Search" (red button)
        searchButton = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'button.Button-danger-vthZW')
            )
        )
        searchButton.click()
        
        time.sleep(5)
    except:
        print("Button not found, probably already pressed.")


if __name__ == "__main__":
    try:
        fixStuckSonarrQueue()
        time.sleep(5)
        radarrGetWanted()
        time.sleep(5)
        sonarrGetWanted()
    finally:
        # Close the shared browser at the end
        driver.quit()
        print("Browser closed")
