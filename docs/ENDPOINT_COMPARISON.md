# API Endpoint Comparison: Before vs After

## 🔄 Course Data Access

| **Functionality** | **Legacy Endpoint (Still Works)** | **New Hierarchical Endpoint** | **Status** |
|---|---|---|---|
| Get course details | `GET /api/courses/{course_id}` | `GET /api/v1/courses/{course_id}` | ✅ Both work |
| Get course lessons | *Not available* | `GET /api/v1/courses/{course_id}/lessons/` | 🆕 New feature |
| Get specific lesson | *Not available* | `GET /api/v1/courses/{course_id}/lessons/{lesson_id}` | 🆕 New feature |
| Get lesson topics | *Not available* | `GET /api/v1/courses/{course_id}/lessons/{lesson_id}/topics/` | 🆕 New feature |
| Get topic tasks | *Not available* | `GET /api/v1/courses/{course_id}/lessons/{lesson_id}/topics/{topic_id}/tasks/` | 🆕 New feature |

## 👨‍🎓 User Progress & Enrollment

| **Functionality** | **Legacy Endpoint** | **New Hierarchical Endpoint** | **Status** |
|---|---|---|---|
| Course enrollment | `POST /api/course/enroll` | `POST /api/v1/users/{user_id}/enroll` | ✅ Enhanced |
| User profile | *Scattered across endpoints* | `GET /api/v1/users/{user_id}/profile` | 🆕 Consolidated |
| Course progress | *Not available* | `GET /api/v1/users/{user_id}/courses/{course_id}/progress` | 🆕 New feature |
| Lesson progress | *Not available* | `GET /api/v1/users/{user_id}/courses/{course_id}/lessons/{lesson_id}/progress` | 🆕 New feature |
| Submit task | `POST /api/submissions` | `POST /api/v1/users/{user_id}/submissions` | 🆕 User-centric |
| Submit solution | `POST /api/solutions` | `POST /api/v1/users/{user_id}/solutions` | 🆕 User-centric |

## 🔐 Authentication & Sessions

| **Functionality** | **Legacy Endpoint** | **New Hierarchical Endpoint** | **Enhancement** |
|---|---|---|---|
| Telegram link | `POST /api/auth/telegram/link` | `POST /api/v1/auth/telegram/link` | ✅ + course_id support |
| Complete auth | `POST /api/auth/telegram/complete` | `POST /api/v1/auth/telegram/complete` | ✅ + course_id in response |
| Session management | *Basic* | `POST /api/v1/auth/sessions/create` | 🆕 Enhanced |
| Token refresh | *Not available* | `POST /api/v1/auth/sessions/refresh` | 🆕 New feature |

## 👨‍🏫 Professor Analytics

| **Functionality** | **Legacy Endpoint** | **New Hierarchical Endpoint** | **Status** |
|---|---|---|---|
| Student analytics | `GET /api/analytics/students` | `GET /api/v1/admin/analytics/students` | ✅ Organized |
| Task analytics | `GET /api/analytics/tasks/*` | `GET /api/v1/admin/analytics/tasks/*` | ✅ Organized |
| Student forms | *Scattered* | `GET /api/v1/admin/student-forms` | ✅ Consolidated |
| User management | *Limited* | `GET /api/v1/admin/users` | 🆕 Enhanced |

## 🎯 Key Differences in Data Format

### **Course Data Response**

#### Legacy Format (Still Available)
```javascript
GET /api/courses/1
{
  "courseTitle": "Computational Thinking and Programming",
  "courseOverview": [...],
  "courseContent": [...],
  "courseInstructor": [...]
}
```

#### New Hierarchical Format
```javascript
GET /api/v1/courses/1
{
  "id": 1,
  "title": "Computational Thinking and Programming", 
  "lessons": [
    {
      "id": 1,
      "title": "Introduction",
      "topics": [
        {
          "id": 1,
          "title": "Getting Started",
          "tasks": [...]
        }
      ]
    }
  ]
}
```

### **User Progress (New Feature)**

```javascript
GET /api/v1/users/1/courses/1/progress
{
  "course_id": 1,
  "total_tasks": 399,
  "completed_tasks": 45,
  "completion_percentage": 11.28,
  "points_earned": 221,
  "total_points": 2411,
  "last_activity": "2024-11-12T01:20:34.772068"
}
```

### **Enhanced Telegram Auth Response**

#### Before
```javascript
POST /api/auth/telegram/complete
{
  "status": "ok",
  "user": {...},
  "token": "jwt_token"
}
```

#### After (Enhanced)
```javascript
POST /api/v1/auth/telegram/complete
{
  "status": "ok",
  "user": {...},
  "token": "jwt_token",
  "course_id": 1  // 🆕 NEW: for auto-enrollment
}
```

## 🚀 Migration Strategy

### **Phase 1: No Action Required** ✅
- All existing code continues to work
- Legacy endpoints return same data format
- Zero breaking changes

### **Phase 2: Enhanced Features** 🆕
```javascript
// Add new features using new endpoints
const userProgress = await fetch(`/api/v1/users/${userId}/courses/${courseId}/progress`);
const userProfile = await fetch(`/api/v1/users/${userId}/profile`);

// Enhanced Telegram enrollment with course_id
if (telegramAuthResponse.course_id) {
  await enrollUserInCourse(telegramAuthResponse.user.id, telegramAuthResponse.course_id);
  router.push(`/courses/${telegramAuthResponse.course_id}`);
}
```

### **Phase 3: Gradual Migration** 🔄
```javascript
// Replace legacy calls gradually
// OLD: const course = await fetch(`/api/courses/${courseId}`);
// NEW: const course = await fetch(`/api/v1/courses/${courseId}`);
```

## ✅ **Bottom Line for Frontend**

1. **Nothing breaks** - all existing code continues to work
2. **New features available** - enhanced progress tracking, hierarchical navigation
3. **Better Telegram flow** - automatic course enrollment with course_id
4. **Migrate at your pace** - no pressure to change everything at once
5. **Future-proof** - ready for microservices when we scale

The API restructure provides immediate benefits while maintaining 100% backward compatibility!