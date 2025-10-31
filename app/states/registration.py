from aiogram.fsm.state import State, StatesGroup

class GeneralRegistration(StatesGroup):
    choosing_language = State()
    choosing_role = State()

class ParentRegistration(StatesGroup):
    confirming_creation = State()
    entering_first_name = State()
    entering_last_name = State()
    entering_phone = State()
    entering_email = State()
    confirming_profile = State() 
    editing_profile = State() 
    adding_child_decision = State()
    asking_child_registered = State()
    entering_child_phone = State()
    confirming_found_child = State()

class StudentRegistration(StatesGroup):
    confirming_creation = State()
    asking_if_registered = State() 
    entering_existing_phone = State() 
    confirming_found_user = State() 
    entering_first_name = State()
    entering_last_name = State()
    entering_dob = State()
    entering_dob_manually = State()
    entering_city = State()
    entering_city_manually = State()
    entering_phone = State()
    entering_parent_name = State()      
    entering_parent_phone = State()
    confirming_profile = State()
    confirming_exode_creation = State() 
    choosing_goal = State()
    editing_profile = State()

class ChildRegistration(StatesGroup):
    entering_child_phone = State() 
    confirming_found_child = State()
    entering_first_name = State()
    entering_last_name = State()
    entering_dob = State()
    entering_dob_manually = State()
    entering_class = State()
    entering_city = State()
    entering_city_manually = State()
    choosing_interests = State()
    confirming_child = State()
    confirming_exode_creation = State()

class ProfileEditing(StatesGroup):
    showing_profile = State()
    choosing_field_to_edit = State()
    editing_field = State()
    managing_children = State()
    viewing_child_details = State()

class StemNavigator(StatesGroup):
    showing_test_info = State()
    taking_test = State()
    viewing_results = State()

class ParentActions(StatesGroup):
    choosing_child_for_test = State()

class Programs(StatesGroup):
    choosing_direction = State()      
    choosing_subcategory = State()   
    choosing_course = State()        
    viewing_course = State()        

class Universities(StatesGroup):
    choosing_city = State() 
    choosing_uni_type = State()
    choosing_university = State()
    choosing_faculty = State()
    choosing_program = State()    
    viewing_faculty = State()

class Support(StatesGroup):
    active_chat = State()

class ProfessionsExplorer(StatesGroup):
    choosing_scale = State()
    choosing_direction = State()
    choosing_profession = State()
    viewing_profession = State()
