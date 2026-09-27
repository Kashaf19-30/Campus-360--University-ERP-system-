export const ALL_PERMISSIONS = ['*'];

export const mockAdminUser = {
  user_id: 1,
  username: 'admin_user',
  user_type: 'admin',
  email: 'admin@test.edu',
};

export const mockStudentUser = {
  user_id: 2,
  username: 'student_user',
  user_type: 'student',
  email: 'student@test.edu',
  registration_number: '2024-CS-001',
};

export const mockTeacherUser = {
  user_id: 3,
  username: 'teacher_user',
  user_type: 'teacher',
  email: 'teacher@test.edu',
};

export const mockApplicantUser = {
  user_id: 4,
  username: 'applicant_user',
  user_type: 'applicant',
  email: 'applicant@test.edu',
};

export const mockFinanceUser = {
  user_id: 5,
  username: 'finance_user',
  user_type: 'finance_officer',
  email: 'finance@test.edu',
};

export const studentPermissions = [
  'enrollments.view_own_enrollment',
  'examinations.view_own_grades',
  'attendance.view_own_attendance',
  'fees.view_own_fees',
  'complaints.view_own_complaint',
  'complaints.create_complaint',
  'announcements.view_announcement',
];

export const teacherPermissions = [
  'academics.view_offering',
  'attendance.mark_attendance',
  'examinations.view_examination',
  'announcements.view_announcement',
  'announcements.create_announcement',
];

export const financePermissions = [
  'fees.view_fees',
  'fees.manage_fees',
];

export const completeStudentProfile = {
  registration_number: '2024-CS-001',
  status: 'active',
  profile: {
    blood_group: 'A+',
    guardian_phone: '03001234567',
    guardian_occupation: 'Engineer',
    residential_address: '123 Main Street Lahore',
    profile_locked: false,
  },
};

export const completeTeacherProfile = {
  profile_completed: true,
  employee_code: 'FAC-001',
  username: 'teacher_user',
  email: 'teacher@test.edu',
};

export const emptyApplicantProfile = {
  firstName: '',
  lastName: '',
  fatherName: '',
  username: 'applicant_user',
  dob: '',
  religion: '',
  cellPhone: '',
  disability: false,
  gender: '',
  cnic: '',
  maritalStatus: '',
  nationality: '',
  profileImage: null,
  residence: { perm_country: '', perm_state: '', perm_city: '', perm_address: '' },
  emergency: { name: '', relation: '', phone: '' },
  guardian: { name: '', cnic: '', relation: '' },
};
