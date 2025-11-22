# eVoting System - Flask Project

This is a simple **eVoting system** built using **Flask**, **MySQL**, and **Flask-Session**. It allows users to register as **voters** or **admin**, cast votes for candidates, and view results. The application includes role-based access control and session management.

---

## Features
    ### User Features
    - User registration (voter or admin)
    - Login / logout functionality
    - Voter dashboard for casting votes
    - Prevents multiple votes for the same position
    - View election results
    
    ### Admin Features
    - Admin dashboard for managing the system
    - Add Provinces and Districts
    - Add candidates for different positions (MPA / MNA)
    - View top candidates
    
    ### Voting Features
    - Vote by region (Province / District)
    - Vote for MPA or MNA candidates
    - Real-time vote counting
    
    ---
    
    ## Technology Stack
    
    - **Backend:** Python, Flask  
    - **Database:** MySQL  
    - **Session Management:** Flask-Session  
    - **Frontend:** HTML, CSS (via Flask templates)  
