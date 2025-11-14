#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>

#define MAX_COURSES 100
#define MAX_NAME 64

/* adjacency matrix: adj[i][j] == 1 means edge from i -> j (i is prereq of j) */
int adj[MAX_COURSES][MAX_COURSES];
char courses[MAX_COURSES][MAX_NAME];
int course_count = 0;

/* helpers to trim newline and whitespace */
void trim_newline(char *s) {
    size_t n = strlen(s);
    if (n == 0) return;
    if (s[n-1] == '\n') s[n-1] = '\0';
    /* trim trailing spaces */
    while (n>0 && isspace((unsigned char)s[n-1])) {
        s[n-1] = '\0';
        n--;
    }
}

/* find course index by name, return -1 if not found */
int find_course(const char *name) {
    for (int i = 0; i < course_count; ++i) {
        if (strcmp(courses[i], name) == 0) return i;
    }
    return -1;
}

/* add a new course with no prerequisites */
void add_course() {
    if (course_count >= MAX_COURSES) {
        printf("Maximum number of courses reached (%d)\n", MAX_COURSES);
        return;
    }
    char name[MAX_NAME];
    printf("Enter course name: ");
    if (!fgets(name, sizeof(name), stdin)) return;
    trim_newline(name);
    if (strlen(name) == 0) {
        printf("Course name cannot be empty.\n");
        return;
    }
    if (find_course(name) != -1) {
        printf("Course '%s' already exists.\n", name);
        return;
    }
    strncpy(courses[course_count], name, MAX_NAME-1);
    courses[course_count][MAX_NAME-1] = '\0';
    /* init adjacency row/col for this new index */
    for (int i = 0; i <= course_count; ++i) {
        adj[course_count][i] = 0;
        adj[i][course_count] = 0;
    }
    course_count++;
    printf("Added course '%s' (index %d).\n", name, course_count-1);
}

/* DFS based cycle detection helper */
int dfs_cycle_util(int v, int visited[], int recstack[]) {
    visited[v] = 1;
    recstack[v] = 1;
    for (int u = 0; u < course_count; ++u) {
        if (adj[v][u]) {
            if (!visited[u]) {
                if (dfs_cycle_util(u, visited, recstack)) return 1;
            } else if (recstack[u]) {
                return 1; /* cycle */
            }
        }
    }
    recstack[v] = 0;
    return 0;
}

/* Check if there is any cycle in graph */
int has_cycle() {
    int visited[MAX_COURSES] = {0};
    int recstack[MAX_COURSES] = {0};
    for (int i = 0; i < course_count; ++i) {
        if (!visited[i]) {
            if (dfs_cycle_util(i, visited, recstack)) return 1;
        }
    }
    return 0;
}

/* Add prerequisite: prereq_name must be taken before course_name
   Edge direction: prereq -> course
   Check for cycles and undo if cycle detected */
void add_prerequisite() {
    char course[MAX_NAME], prereq[MAX_NAME];
    printf("Enter course name (the course that requires a prereq): ");
    if (!fgets(course, sizeof(course), stdin)) return;
    trim_newline(course);
    printf("Enter prerequisite course name (must be taken before the course): ");
    if (!fgets(prereq, sizeof(prereq), stdin)) return;
    trim_newline(prereq);

    if (strlen(course) == 0 || strlen(prereq) == 0) {
        printf("Course names cannot be empty.\n");
        return;
    }

    int ci = find_course(course);
    int pi = find_course(prereq);

    if (ci == -1) {
        printf("Course '%s' not found. Add it first.\n", course);
        return;
    }
    if (pi == -1) {
        printf("Prerequisite course '%s' not found. Add it first.\n", prereq);
        return;
    }

    if (adj[pi][ci]) {
        printf("Prerequisite already exists: '%s' -> '%s'\n", prereq, course);
        return;
    }

    /* add edge */
    adj[pi][ci] = 1;

    /* check for cycle; if cycle undo and warn */
    if (has_cycle()) {
        adj[pi][ci] = 0;
        printf("Cannot add prerequisite '%s' -> '%s' because it creates a cycle.\n", prereq, course);
    } else {
        printf("Prerequisite added: '%s' -> '%s'\n", prereq, course);
    }
}

/* Display immediate prerequisites (incoming edges) for a course */
void display_prereqs() {
    char name[MAX_NAME];
    printf("Enter course name: ");
    if (!fgets(name, sizeof(name), stdin)) return;
    trim_newline(name);
    if (strlen(name) == 0) {
        printf("Course name cannot be empty.\n");
        return;
    }
    int idx = find_course(name);
    if (idx == -1) {
        printf("Course '%s' not found.\n", name);
        return;
    }
    printf("Immediate prerequisites for '%s':\n", name);
    int found = 0;
    for (int i = 0; i < course_count; ++i) {
        if (adj[i][idx]) {
            printf(" - %s\n", courses[i]);
            found = 1;
        }
    }
    if (!found) printf(" (none)\n");
}

/* Topological sort using Kahn's algorithm; prints one possible ordering */
void topo_sort() {
    if (course_count == 0) {
        printf("No courses in the system.\n");
        return;
    }
    int indeg[MAX_COURSES] = {0};
    for (int i = 0; i < course_count; ++i) {
        for (int j = 0; j < course_count; ++j) {
            if (adj[i][j]) indeg[j]++;
        }
    }
    /* queue for nodes with indegree 0 */
    int q[MAX_COURSES];
    int qh = 0, qt = 0;
    for (int i = 0; i < course_count; ++i) if (indeg[i] == 0) q[qt++] = i;

    int cnt = 0;
    int order[MAX_COURSES];

    while (qh < qt) {
        int v = q[qh++]; /* dequeue */
        order[cnt++] = v;
        for (int u = 0; u < course_count; ++u) {
            if (adj[v][u]) {
                indeg[u]--;
                if (indeg[u] == 0) q[qt++] = u;
            }
        }
    }

    if (cnt != course_count) {
        printf("No valid ordering (graph has a cycle).\n");
        return;
    }

    printf("One valid order to take all courses:\n");
    for (int i = 0; i < cnt; ++i) {
        printf("%d. %s\n", i+1, courses[order[i]]);
    }
}

/* utility to print all courses with their indices */
void print_all_courses() {
    if (course_count == 0) {
        printf("No courses added yet.\n");
        return;
    }
    printf("Courses:\n");
    for (int i = 0; i < course_count; ++i) {
        printf(" [%d] %s\n", i, courses[i]);
    }
}

/* menu loop */
int main() {
    /* initialize adjacency */
    for (int i = 0; i < MAX_COURSES; ++i)
        for (int j = 0; j < MAX_COURSES; ++j)
            adj[i][j] = 0;

    printf("University Course Prerequisite Checker\n");
    printf("=====================================\n");

    while (1) {
        printf("\nMenu:\n");
        printf(" 1. Add a new course (no prerequisites)\n");
        printf(" 2. Add a prerequisite relation (prereq -> course)\n");
        printf(" 3. Display immediate prerequisites for a course\n");
        printf(" 4. Check if current graph has a cycle\n");
        printf(" 5. Determine a valid sequence for all courses (Topological Sort)\n");
        printf(" 6. List all courses\n");
        printf(" 0. Exit\n");
        printf("Choose an option: ");

        char line[32];
        if (!fgets(line, sizeof(line), stdin)) break;
        int choice = atoi(line);

        switch (choice) {
            case 1: add_course(); break;
            case 2: add_prerequisite(); break;
            case 3: display_prereqs(); break;
            case 4:
                if (has_cycle()) printf("Graph has a cycle.\n");
                else printf("No cycle detected (graph is a DAG).\n");
                break;
            case 5: topo_sort(); break;
            case 6: print_all_courses(); break;
            case 0:
                printf("Exiting. Goodbye!\n");
                return 0;
            default:
                printf("Invalid choice. Try again.\n");
        }
    }
    return 0;
}