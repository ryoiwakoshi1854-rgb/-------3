document.addEventListener('DOMContentLoaded', () => {
    generateTimetableGrid();
    loadCourses();
});

// 1〜6限のマス目を自動で作る関数
function generateTimetableGrid() {
    const tbody = document.getElementById('timetableBody');
    const days = ['月', '火', '水', '木', '金', '土'];
    
    for (let period = 1; period <= 6; period++) {
        const tr = document.createElement('tr');
        // 時限の数字セル
        const tdPeriod = document.createElement('td');
        tdPeriod.className = 'period-col';
        tdPeriod.textContent = period;
        tr.appendChild(tdPeriod);

        // 各曜日のセル
        days.forEach(day => {
            const td = document.createElement('td');
            td.id = `cell-${day}-${period}`; // 例: cell-月-3
            td.className = 'timetable-cell';
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    }
}

async function searchAndAdd() {
    const queryInput = document.getElementById('courseQuery');
    const query = queryInput.value;
    if (query === '') return;

    const loadingMsg = document.getElementById('loadingMessage');
    loadingMsg.style.display = 'block';
    loadingMsg.innerHTML = `⌛ 「${query}」を解析中...`;
    queryInput.value = '';

    try {
        const response = await fetch('http://localhost:8000/scrape-syllabus', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });
        
        const result = await response.json();
        loadingMsg.style.display = 'none';

        if (result.status === "success") {
            saveCourse(result.data);
            loadCourses(); 
        } else {
            alert("エラー: " + result.message);
        }
    } catch (error) {
        loadingMsg.style.display = 'none';
        alert("通信エラーが発生しました。");
    }
}

function saveCourse(courseData) {
    let courses = JSON.parse(localStorage.getItem('myCourses')) || [];
    courses.push(courseData);
    localStorage.setItem('myCourses', JSON.stringify(courses));
}

function loadCourses() {
    // 一旦すべてのマス目とリストを空にする
    document.querySelectorAll('.timetable-cell').forEach(cell => cell.innerHTML = '');
    document.getElementById('unassignedList').innerHTML = '';

    let courses = JSON.parse(localStorage.getItem('myCourses')) || [];
    courses.forEach(course => {
        renderCourse(course);
    });
}

function renderCourse(data) {
    // カードのHTML（時間割に入るようにコンパクトに）
    const card = document.createElement('div');
    card.className = 'course-card';

    const teacherHtml = (data.teacher && data.teacher !== "不明") ? `<div class="info">👤 ${data.teacher}</div>` : "";
    const roomHtml = (data.room && data.room !== "不明") ? `<div class="info">📍 ${data.room}</div>` : "";

    card.innerHTML = `
        <button class="delete-btn" onclick="deleteCourse('${data.id}')">×</button>
        <div class="course-title">${data.course}</div>
        ${teacherHtml}
        ${roomHtml}
        <a href="${data.url}" target="_blank" class="syllabus-link">🔗 シラバス</a>
    `;

    // 「月3」などから曜日と時限を解析
    const timeMatch = data.time_slot ? data.time_slot.match(/(月|火|水|木|金|土)\s*(\d)/) : null;

    if (timeMatch) {
        // 例：day="月", period="3"
        const day = timeMatch[1];
        const period = timeMatch[2];
        const targetCell = document.getElementById(`cell-${day}-${period}`);
        
        if (targetCell) {
            targetCell.appendChild(card);
            return; // 成功したらここで終了
        }
    }

    // 解析失敗、または曜日不明の場合は「その他の授業」エリアへ
    document.getElementById('unassignedList').appendChild(card);
}

function deleteCourse(id) {
    if (!confirm("この授業を削除しますか？")) return;
    let courses = JSON.parse(localStorage.getItem('myCourses')) || [];
    courses = courses.filter(c => c.id !== id);
    localStorage.setItem('myCourses', JSON.stringify(courses));
    loadCourses();
}