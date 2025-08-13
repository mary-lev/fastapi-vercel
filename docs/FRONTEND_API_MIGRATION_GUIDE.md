# FastAPI v2.0 - Frontend Migration Guide

## 🎯 Overview

We've successfully implemented **Phase 1** of the API restructuring proposal while maintaining **100% backward compatibility**. Your frontend will continue working unchanged, but now you have access to a cleaner, more hierarchical API structure.

## 📊 What's Changed

### ✅ **Backward Compatibility Maintained**
All existing endpoints continue to work exactly as before:
- ✅ `GET /api/courses/{course_id}` - **Still works** (returns same data format)
- ✅ All original endpoints preserved
- ✅ Same response formats maintained
- ✅ No breaking changes

### 🆕 **New Hierarchical Endpoints Available**
You can now optionally use the new structured endpoints:

```
📚 Learning Content Service
├── GET /api/v1/courses/
├── GET /api/v1/courses/{course_id}
├── GET /api/v1/courses/{course_id}/lessons/
├── GET /api/v1/courses/{course_id}/lessons/{lesson_id}
├── GET /api/v1/courses/{course_id}/lessons/{lesson_id}/topics/
├── GET /api/v1/courses/{course_id}/lessons/{lesson_id}/topics/{topic_id}
├── GET /api/v1/courses/{course_id}/lessons/{lesson_id}/topics/{topic_id}/tasks/
└── GET /api/v1/courses/{course_id}/lessons/{lesson_id}/topics/{topic_id}/tasks/{task_id}
```

## 🔧 Migration Strategy

### **Option 1: Keep Everything As-Is** ✨
```javascript
// This still works exactly the same
const courseData = await fetch(`/api/courses/${courseId}`);
// Returns the exact same format you expect
```

### **Option 2: Gradual Migration** 🚀
```javascript
// New hierarchical approach (optional)
const courseData = await fetch(`/api/v1/courses/${courseId}`);
const userProgress = await fetch(`/api/v1/users/${userId}/courses/${courseId}/progress`);
const userProfile = await fetch(`/api/v1/users/${userId}/profile`);
```

### **Option 3: Hybrid Approach** ⚡
```javascript
// Use legacy for existing features
const courseData = await fetch(`/api/courses/${courseId}`);

// Use new endpoints for new features
const detailedProgress = await fetch(`/api/v1/users/${userId}/courses/${courseId}/progress`);
```

## 🎨 New Frontend Opportunities

### **1. Enhanced User Progress Tracking**
```javascript
// Get comprehensive user progress
const progress = await fetch(`/api/v1/users/${userId}/courses/${courseId}/progress`);
/* Returns:
{
  "course_id": 1,
  "total_tasks": 399,
  "completed_tasks": 45,
  "completion_percentage": 11.28,
  "points_earned": 221,
  "total_points": 2411,
  "last_activity": "2024-11-12T01:20:34.772068"
}
*/

// Get lesson-level progress
const lessonProgress = await fetch(`/api/v1/users/${userId}/courses/${courseId}/lessons/${lessonId}/progress`);
```

### **2. Improved Course Enrollment Flow**
```javascript
// Enhanced enrollment with course-specific Telegram links
const enrollment = await fetch(`/api/v1/users/${userId}/enroll`, {
  method: 'POST',
  body: JSON.stringify({ course_id: courseId })
});
```

### **3. Hierarchical Content Navigation**
```javascript
// Build breadcrumb navigation
const course = await fetch(`/api/v1/courses/${courseId}`);
const lesson = await fetch(`/api/v1/courses/${courseId}/lessons/${lessonId}`);
const topic = await fetch(`/api/v1/courses/${courseId}/lessons/${lessonId}/topics/${topicId}`);
```

## 🔄 Telegram Course Enrollment Integration

### **Enhanced Flow**
The Telegram authentication now supports **course-specific enrollment**:

1. **Backend generates course-specific link**:
   ```
   POST /api/v1/auth/telegram/link
   { "telegram_user_id": 12345, "course_id": 1 }
   ```

2. **User completes authentication**:
   ```
   POST /api/v1/auth/telegram/complete
   { "token": "jwt_token" }
   ```

3. **Frontend receives course_id in response**:
   ```javascript
   const authResponse = await fetch('/api/v1/auth/telegram/complete', { ... });
   // Response includes: { "user": {...}, "course_id": 1, "token": "..." }
   ```

4. **Frontend automatically enrolls user**:
   ```javascript
   if (authResponse.course_id) {
     await fetch(`/api/v1/users/${authResponse.user.id}/enroll`, {
       method: 'POST',
       body: JSON.stringify({ course_id: authResponse.course_id })
     });
     
     // Redirect to course page
     router.push(`/courses/${authResponse.course_id}`);
   }
   ```

## 📋 Complete Endpoint Reference

### **Legacy Endpoints (Still Available)**
```
GET /api/courses/{course_id}           # Course data (original format)
POST /api/course/enroll               # Course enrollment  
POST /api/auth/telegram/link          # Telegram auth
POST /api/auth/telegram/complete      # Complete Telegram auth
```

### **New Hierarchical Endpoints**

#### **📚 Learning Content** (`/api/v1/courses`)
```
GET    /api/v1/courses/                                    # List all courses
GET    /api/v1/courses/{course_id}                         # Course details (new format)
GET    /api/v1/courses/{course_id}/lessons/                # Course lessons
GET    /api/v1/courses/{course_id}/lessons/{lesson_id}     # Lesson details
PUT    /api/v1/courses/{course_id}/lessons/{lesson_id}/topics/{topic_id}/tasks/{task_id}  # Update task
```

#### **👨‍🎓 Student Progress** (`/api/v1/users`)
```
GET    /api/v1/users/{user_id}/profile                     # User profile
GET    /api/v1/users/{user_id}/courses/                    # User's enrolled courses
GET    /api/v1/users/{user_id}/courses/{course_id}/progress            # Course progress
GET    /api/v1/users/{user_id}/courses/{course_id}/lessons/{lesson_id}/progress  # Lesson progress
POST   /api/v1/users/{user_id}/submissions                 # Submit task attempt
GET    /api/v1/users/{user_id}/submissions                 # Get user submissions
POST   /api/v1/users/{user_id}/solutions                   # Submit task solution
GET    /api/v1/users/{user_id}/solutions                   # Get user solutions
GET    /api/v1/users/{user_id}/sessions                    # User sessions
POST   /api/v1/users/{user_id}/enroll                      # Enroll in course
```

#### **🔐 Authentication** (`/api/v1/auth`)
```
POST   /api/v1/auth/login                    # Standard login (placeholder)
POST   /api/v1/auth/logout                   # Logout
POST   /api/v1/auth/telegram/link            # Create Telegram link (enhanced)
POST   /api/v1/auth/telegram/complete        # Complete Telegram auth (enhanced)
GET    /api/v1/auth/telegram/status/{id}     # Check Telegram status
POST   /api/v1/auth/sessions/create          # Create session
POST   /api/v1/auth/sessions/refresh         # Refresh token
GET    /api/v1/auth/health                   # Auth service health
```

#### **👨‍🏫 Professor Analytics** (`/api/v1/admin`)
```
GET    /api/v1/admin/analytics/students                    # Student analytics
GET    /api/v1/admin/analytics/tasks/daily                 # Daily task analytics
GET    /api/v1/admin/analytics/tasks/completion            # Task completion analytics
GET    /api/v1/admin/analytics/tasks/{task_id}/progress    # Task-specific progress
GET    /api/v1/admin/student-forms                         # Student form submissions
POST   /api/v1/admin/task-generator/generate               # Generate tasks (placeholder)
GET    /api/v1/admin/users                                 # Manage users
GET    /api/v1/admin/system/stats                          # System statistics
```

## 🚀 Benefits for Frontend Development

### **Immediate Benefits**
- **Clear service boundaries**: Know where to find specific functionality
- **Intuitive URLs**: `/courses/{id}/lessons/{id}/topics/{id}/tasks/{id}`
- **Better error handling**: Service-specific error responses
- **Improved documentation**: Auto-generated docs show clear hierarchy

### **Progressive Enhancement**
- **Start using new endpoints gradually**
- **Mix old and new approaches**
- **No pressure to migrate everything at once**
- **Full backward compatibility maintained**

### **Future-Proof Architecture**
- **Microservices ready**: When we split services, URLs won't change
- **Independent scaling**: Different services can be optimized separately
- **Team autonomy**: Frontend team can choose migration pace

## 🛠️ Development Tools

### **API Documentation**
- **New docs**: http://localhost:8000/docs (shows hierarchical structure)
- **Service discovery**: `GET /api` (lists all available services)
- **Health checks**: `GET /health` (system status)

### **Testing**
```bash
# Test new endpoints
curl http://localhost:8000/api/v1/courses/
curl http://localhost:8000/api/v1/users/1/profile
curl http://localhost:8000/api/v1/admin/analytics/students

# Verify legacy endpoints still work
curl http://localhost:8000/api/courses/1
```

## ⚠️ Important Notes

### **No Breaking Changes**
- All existing frontend code continues to work unchanged
- Same response formats maintained for legacy endpoints
- Database structure unchanged

### **Enhanced Telegram Flow**
- Course enrollment now happens automatically after Telegram auth
- `course_id` parameter added to auth links
- Frontend receives `course_id` in auth response for auto-enrollment

### **Migration Timeline**
- **Immediate**: No action required - everything keeps working
- **Optional**: Start using new endpoints for new features
- **Future**: Gradually migrate to new structure as needed

## 🎯 Recommended Next Steps

1. **Keep existing code as-is** - everything works unchanged
2. **Try new user progress endpoints** for enhanced UX
3. **Use new Telegram enrollment flow** for course-specific links
4. **Explore hierarchical course navigation** when building new features
5. **Migrate gradually** - no rush, no breaking changes

The new API structure provides immediate benefits while maintaining full compatibility. You can adopt new features at your own pace!