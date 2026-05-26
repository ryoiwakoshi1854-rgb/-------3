// script.js (全体コード)

// ⚠️ 【重要】以下の 'https://xxxx.onrender.com' の部分を、
// あなたのRenderの画面上部に表示されている「本物のURL」に書き換えてください。
// ※ 末尾の / は無しにしてください（例: https://my-service.onrender.com）
const RENDER_API_URL = 'https://xxxx.onrender.com';

document.getElementById('search-btn').addEventListener('click', async () => {
    const query = document.getElementById('search-query').value;
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '検索中...';

    if (!query) {
        resultsDiv.innerHTML = 'キーワードを入力してください。';
        return;
    }

    try {
        // RenderのAPIを呼び出す
        const response = await fetch(`${RENDER_API_URL}/scrape-syllabus?query=${encodeURIComponent(query)}`);
        
        if (!response.ok) {
            throw new Error(`サーバーエラー: ${response.status}`);
        }

        const data = await response.json();
        resultsDiv.innerHTML = '';

        if (data.length === 0) {
            resultsDiv.innerHTML = '該当する授業が見つかりませんでした。';
            return;
        }

        // 検索結果のカードを生成
        data.forEach(course => {
            const card = document.createElement('div');
            card.className = 'course-card';
            
            // データが正しく取得できているか、念のためフォールバック（||）を設定
            const title = course.title || '名称不明の授業';
            const teacher = course.teacher || '担当者不明';
            const day = course.day || '未定';
            const period = course.period || '未定';

            card.innerHTML = `
                <h4>${title}</h4>
                <p>担当: ${teacher}</p>
                <p>曜日・時限: ${day}${period ? period + '限' : ''}</p>
                <button onclick="addCourseToTimetable('${title}', '${day}', '${period}')">時間割に追加</button>
            `;
            resultsDiv.appendChild(card);
        });

    } catch (error) {
        console.error('エラー詳細:', error);
        resultsDiv.innerHTML = 'データの取得に失敗しました。Renderサーバーが起動中か確認してください。';
    }
});

// 時間割にセルを追加する関数
function addCourseToTimetable(title, day, period) {
    if (!day || !period || day === '未定' || period === '未定') {
        alert('曜日または時限が特定できないため、時間割に自動配置できません。');
        return;
    }

    // 例: "月", "1" -> "cell-月-1" のようなIDを持つHTML要素を探す
    const cellId = `cell-${day}-${period}`;
    const cell = document.getElementById(cellId);

    if (cell) {
        cell.innerHTML = `<strong>${title}</strong>`;
        alert(`${title} を時間割に追加しました！`);
    } else {
        alert('該当する時間割の枠（セル）が見つかりませんでした。HTMLのIDを確認してください。');
    }
}