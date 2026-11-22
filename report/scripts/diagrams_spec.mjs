export const DIAGRAMS = [
  {
    name: "hinh-1-1-bai-toan-da-kenh",
    width: 1120,
    scale: 2,
    body: `
      <style>
        .h1-wrap {
          border: 1.5px solid #cbd5e1;
          border-radius: 14px;
          padding: 20px 22px;
          background: #ffffff;
        }
        .h1-title {
          text-align: center;
          font-size: 17px;
          font-weight: 700;
          color: #0f172a;
          margin-bottom: 18px;
          letter-spacing: 0.2px;
        }
        .h1-grid {
          display: grid;
          grid-template-columns: 1fr 54px 1.26fr 54px 1.08fr;
          align-items: stretch;
        }
        .col {
          display: flex;
          flex-direction: column;
        }
        .col-head {
          font-size: 12px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: #475569;
          text-align: center;
          margin-bottom: 10px;
          min-height: 18px;
        }
        .col-cards {
          flex: 1;
          display: flex;
          flex-direction: column;
          justify-content: center;
          gap: 14px;
        }
        .card {
          border-radius: 10px;
          padding: 13px 15px;
          background: #f8fafc;
          border: 1.5px solid #94a3b8;
          box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }
        .card.blue { border-color: #2563eb; background: #eff6ff; }
        .card.teal { border-color: #0d9488; background: #f0fdfa; }
        .card.amber { border-color: #d97706; background: #fffbeb; }
        .card.purple { border-color: #7c3aed; background: #f5f3ff; }
        .card.slate { border-color: #334155; background: #f8fafc; }
        .badge {
          display: inline-block;
          font-size: 11px;
          font-weight: 700;
          color: #ffffff;
          padding: 2px 9px;
          border-radius: 999px;
          margin-bottom: 7px;
        }
        .blue .badge { background: #1d4ed8; }
        .teal .badge { background: #0f766e; }
        .amber .badge { background: #b45309; }
        .purple .badge { background: #6d28d9; }
        .slate .badge { background: #334155; }
        .card h4 {
          font-size: 14px;
          font-weight: 700;
          color: #0f172a;
          margin-bottom: 5px;
        }
        .card p {
          font-size: 12.5px;
          line-height: 1.45;
          color: #334155;
        }
        .risk-panel {
          border: 1.5px dashed #dc2626;
          border-radius: 12px;
          padding: 14px 15px;
          background: #fef2f2;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .risk-head {
          text-align: center;
          font-size: 13px;
          font-weight: 700;
          color: #991b1b;
          padding-bottom: 4px;
          border-bottom: 1px solid #fecaca;
        }
        .risk-item {
          background: #ffffff;
          border: 1px solid #fca5a5;
          border-radius: 8px;
          padding: 9px 11px;
        }
        .risk-item strong {
          display: block;
          font-size: 12.5px;
          color: #b91c1c;
          margin-bottom: 3px;
        }
        .risk-item span {
          display: block;
          font-size: 12px;
          line-height: 1.42;
          color: #334155;
        }
        .arrows {
          display: flex;
          justify-content: center;
          align-items: center;
          height: 100%;
        }
      </style>
      <div class="h1-wrap">
        <div class="h1-title">BÀI TOÁN HỢP NHẤT ĐẶT HÀNG ĐA KÊNH VÀ CÁC ĐIỂM NGHẼN PHÂN TÁN</div>
        <div class="h1-grid">
          <div class="col">
            <div class="col-head">1. Nguồn phát sinh đơn độc lập</div>
            <div class="col-cards">
              <div class="card blue">
                <span class="badge">Tại quầy (POS01, POS02)</span>
                <h4>Điểm bán trực tiếp</h4>
                <p>Thu ngân lập đơn tại quầy, gửi yêu cầu hủy khi khách đổi ý và vẫn phải nhận đơn khi đứt mạng ra trung tâm.</p>
              </div>
              <div class="card teal">
                <span class="badge">Đặt trực tuyến (Online)</span>
                <h4>Kênh đặt hàng từ xa</h4>
                <p>Tiếp nhận đơn hàng chạy trên tiến trình riêng, phát sinh đơn đồng thời với các quầy bán hàng trực tiếp.</p>
              </div>
            </div>
          </div>

          <div class="arrows">
            <svg width="54" height="240" viewBox="0 0 54 240">
              <defs>
                <marker id="arr1" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                  <path d="M0,1 L7,4 L0,7 Z" fill="#475569"/>
                </marker>
              </defs>
              <path d="M2,66 C24,66 28,110 50,110" fill="none" stroke="#475569" stroke-width="2" marker-end="url(#arr1)"/>
              <path d="M2,180 C24,180 28,132 50,132" fill="none" stroke="#475569" stroke-width="2" marker-end="url(#arr1)"/>
            </svg>
          </div>

          <div class="risk-panel">
            <div class="risk-head">Điểm nghẽn truyền thông &amp; tranh chấp</div>
            <div class="risk-item">
              <strong>1. Chi nhánh mất kết nối mạng</strong>
              <span>Đơn tạo cục bộ chưa tới Bếp/Kho; thu ngân cần biết rõ đơn đã gửi đi hay chưa trước khi chốt hủy.</span>
            </div>
            <div class="risk-item">
              <strong>2. Xung đột nguyên liệu &amp; trạng thái</strong>
              <span>Hai nguồn cùng đặt món dùng chung nguyên liệu tồn hạn chế; yêu cầu hủy trùng lúc Bếp bắt đầu nấu.</span>
            </div>
            <div class="risk-item">
              <strong>3. Tin nhắn lặp hoặc sai thứ tự</strong>
              <span>Mạng chập chờn làm lặp gói tạo đơn hoặc đẩy lệnh hủy tới Bếp trước thông điệp đơn hàng.</span>
            </div>
            <div class="risk-item">
              <strong>4. Độ trễ tổng hợp số liệu</strong>
              <span>Báo cáo quản lý gom từ nhiều nguồn cần hiển thị rõ mốc dữ liệu tính đến cho từng kênh.</span>
            </div>
          </div>

          <div class="arrows">
            <svg width="54" height="280" viewBox="0 0 54 280">
              <defs>
                <marker id="arr2" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                  <path d="M0,1 L7,4 L0,7 Z" fill="#475569"/>
                </marker>
              </defs>
              <path d="M2,122 C24,122 26,52 50,52" fill="none" stroke="#475569" stroke-width="2" marker-end="url(#arr2)"/>
              <path d="M2,140 L50,140" fill="none" stroke="#475569" stroke-width="2" marker-end="url(#arr2)"/>
              <path d="M2,158 C24,158 26,228 50,228" fill="none" stroke="#475569" stroke-width="2" marker-end="url(#arr2)"/>
            </svg>
          </div>

          <div class="col">
            <div class="col-head">2. Xử lý &amp; tổng hợp trung tâm</div>
            <div class="col-cards">
              <div class="card amber">
                <span class="badge">Kho trung tâm</span>
                <h4>Giữ &amp; kiểm soát nguyên liệu</h4>
                <p>Giữ đủ nguyên liệu cho cả đơn hoặc từ chối toàn bộ, tránh giữ trùng và chặn món khi nguyên liệu hỏng.</p>
              </div>
              <div class="card purple">
                <span class="badge">Bếp trung tâm</span>
                <h4>Hợp nhất phiếu &amp; phân xử hủy</h4>
                <p>Nhận phiếu từ cả POS và Online, điều phối chế biến và quyết định duy nhất khi có tranh chấp hủy đơn.</p>
              </div>
              <div class="card slate">
                <span class="badge">Tổng hợp trung tâm</span>
                <h4>Báo cáo hợp nhất gần thời gian thực</h4>
                <p>Gom trạng thái đơn từ tất cả nguồn độc lập kèm mốc thời gian cập nhật của từng kênh.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    `,
  },
];
