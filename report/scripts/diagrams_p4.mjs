export const P4_DIAGRAMS = [
  {
    name: "hinh-4-1-mo-hinh-kiem-thu",
    width: 1080,
    scale: 2,
    body: `
      <div style="border:1.5px solid #cbd5e1;border-radius:14px;background:#ffffff;padding:16px 18px;">
        <svg width="1040" height="585" viewBox="0 0 1040 585" xmlns="http://www.w3.org/2000/svg" style="display:block;font-family:'Segoe UI',Arial,sans-serif;">
          <defs>
            <marker id="tArrB" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
              <path d="M0,1 L7,4 L0,7" fill="none" stroke="#1d4ed8" stroke-width="1.6"/>
            </marker>
            <marker id="tArrR" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
              <path d="M0,1 L7,4 L0,7" fill="none" stroke="#dc2626" stroke-width="1.6"/>
            </marker>
            <marker id="tArrG" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
              <path d="M0,1 L7,4 L0,7" fill="none" stroke="#475569" stroke-width="1.5"/>
            </marker>
          </defs>

          <text x="520" y="24" text-anchor="middle" font-size="15.5" font-weight="700" fill="#0f172a">MÔ HÌNH KIỂM THỬ TÍNH PHÂN TÁN, CHỊU LỖI VÀ HIỆU NĂNG</text>

          <!-- Left column: Test & Load drivers -->
          <rect x="16" y="54" width="244" height="466" rx="12" fill="#f8fafc" stroke="#64748b" stroke-width="1.5"/>
          <text x="138" y="80" text-anchor="middle" font-size="13" font-weight="700" fill="#1e293b">TÁC NHÂN KIỂM THỬ</text>

          <rect x="32" y="100" width="212" height="110" rx="9" fill="#eff6ff" stroke="#2563eb" stroke-width="1.5"/>
          <text x="138" y="123" text-anchor="middle" font-size="12.5" font-weight="700" fill="#1e3a8a">Pytest E2E &amp; Tranh chấp</text>
          <text x="138" y="143" text-anchor="middle" font-size="11" fill="#334155">Tầng 1–3 trên PostgreSQL</text>
          <text x="138" y="160" text-anchor="middle" font-size="11" fill="#334155">&amp; Kafka 3 broker thật</text>
          <text x="138" y="177" text-anchor="middle" font-size="11" fill="#1d4ed8" font-weight="600">Đẩy tải song song đa nguồn</text>
          <text x="138" y="194" text-anchor="middle" font-size="11" fill="#1d4ed8" font-weight="600">POS01 + POS02 + ONLINE</text>

          <rect x="32" y="232" width="212" height="118" rx="9" fill="#fef2f2" stroke="#dc2626" stroke-width="1.5"/>
          <text x="138" y="255" text-anchor="middle" font-size="12.5" font-weight="700" fill="#991b1b">Tiêm lỗi (Docker Engine API)</text>
          <text x="138" y="276" text-anchor="middle" font-size="11" fill="#334155">1. Tách mạng kafka-net</text>
          <text x="138" y="294" text-anchor="middle" font-size="11" fill="#334155">2. Tách mạng replication-net</text>
          <text x="138" y="312" text-anchor="middle" font-size="11" fill="#334155">3. Dừng/kill service container</text>
          <text x="138" y="330" text-anchor="middle" font-size="11" fill="#334155">4. Kill broker leader Kafka</text>

          <rect x="32" y="372" width="212" height="128" rx="9" fill="#f0fdf4" stroke="#15803d" stroke-width="1.5"/>
          <text x="138" y="395" text-anchor="middle" font-size="12.5" font-weight="700" fill="#14532d">Apache JMeter 5.6.3</text>
          <text x="138" y="416" text-anchor="middle" font-size="11" fill="#334155">Phát tải 250 luồng/chức năng</text>
          <text x="138" y="434" text-anchor="middle" font-size="11" fill="#334155">trên mạng api-net</text>
          <text x="138" y="454" text-anchor="middle" font-size="11" fill="#15803d" font-weight="600">Đo thời gian đáp ứng,</text>
          <text x="138" y="472" text-anchor="middle" font-size="11" fill="#15803d" font-weight="600">thông lượng &amp; độ trễ trọn vòng</text>

          <!-- Center column: Running Distributed Cluster -->
          <rect x="316" y="54" width="388" height="466" rx="12" fill="#f8fafc" stroke="#334155" stroke-width="1.6"/>
          <text x="510" y="80" text-anchor="middle" font-size="13" font-weight="700" fill="#0f172a">CỤM HỆ THỐNG PHÂN TÁN (21 CONTAINER)</text>

          <!-- Row 1: Order Sources -->
          <rect x="336" y="96" width="348" height="96" rx="9" fill="#edf7f1" stroke="#15803d" stroke-width="1.4"/>
          <text x="510" y="116" text-anchor="middle" font-size="12" font-weight="700" fill="#14532d">Nhóm nguồn phát sinh đơn &amp; CSDL riêng</text>
          <rect x="350" y="128" width="100" height="50" rx="6" fill="#ffffff" stroke="#15803d"/>
          <text x="400" y="149" text-anchor="middle" font-size="11.5" font-weight="700" fill="#0f172a">POS01</text>
          <text x="400" y="166" text-anchor="middle" font-size="10.5" fill="#475569">pos01-db</text>
          <rect x="460" y="128" width="100" height="50" rx="6" fill="#ffffff" stroke="#15803d"/>
          <text x="510" y="149" text-anchor="middle" font-size="11.5" font-weight="700" fill="#0f172a">POS02</text>
          <text x="510" y="166" text-anchor="middle" font-size="10.5" fill="#475569">pos02-db</text>
          <rect x="570" y="128" width="100" height="50" rx="6" fill="#ffffff" stroke="#0d9488"/>
          <text x="620" y="149" text-anchor="middle" font-size="11.5" font-weight="700" fill="#0f172a">ONLINE</text>
          <text x="620" y="166" text-anchor="middle" font-size="10.5" fill="#475569">online-db</text>

          <!-- Cut badge 1 between Sources and Kafka -->
          <line x1="510" y1="192" x2="510" y2="230" stroke="#475569" stroke-width="1.6"/>
          <rect x="412" y="200" width="196" height="22" rx="11" fill="#fef2f2" stroke="#dc2626" stroke-width="1.2"/>
          <text x="510" y="215" text-anchor="middle" font-size="10.5" font-weight="700" fill="#991b1b">Điểm cắt 1: Tách mạng kafka-net</text>

          <!-- Row 2: Kafka KRaft Cluster -->
          <rect x="336" y="232" width="348" height="72" rx="9" fill="#f3f0fc" stroke="#7c3aed" stroke-width="1.4"/>
          <text x="510" y="254" text-anchor="middle" font-size="12" font-weight="700" fill="#4c1d95">Apache Kafka KRaft (RF = 3, min.insync = 2)</text>
          <rect x="352" y="264" width="96" height="28" rx="6" fill="#ffffff" stroke="#7c3aed"/>
          <text x="400" y="282" text-anchor="middle" font-size="11" font-weight="600" fill="#0f172a">kafka1</text>
          <rect x="462" y="264" width="96" height="28" rx="6" fill="#ffffff" stroke="#7c3aed"/>
          <text x="510" y="282" text-anchor="middle" font-size="11" font-weight="600" fill="#0f172a">kafka2</text>
          <rect x="572" y="264" width="96" height="28" rx="6" fill="#ffffff" stroke="#7c3aed"/>
          <text x="620" y="282" text-anchor="middle" font-size="11" font-weight="600" fill="#0f172a">kafka3</text>

          <line x1="422" y1="304" x2="422" y2="334" stroke="#475569" stroke-width="1.6"/>
          <line x1="598" y1="304" x2="598" y2="334" stroke="#475569" stroke-width="1.6"/>

          <!-- Row 3: Inventory x2 & Kitchen -->
          <rect x="336" y="336" width="170" height="78" rx="9" fill="#fbf5e8" stroke="#b45309" stroke-width="1.4"/>
          <text x="421" y="357" text-anchor="middle" font-size="12" font-weight="700" fill="#78350f">Inventory ×2</text>
          <text x="421" y="375" text-anchor="middle" font-size="10.5" fill="#334155">inventory-1 / inventory-2</text>
          <text x="421" y="394" text-anchor="middle" font-size="10.5" font-weight="600" fill="#b45309">inventory-db (khóa dòng)</text>

          <rect x="518" y="336" width="166" height="78" rx="9" fill="#fbf5e8" stroke="#b45309" stroke-width="1.4"/>
          <text x="601" y="357" text-anchor="middle" font-size="12" font-weight="700" fill="#78350f">Kitchen Service</text>
          <text x="601" y="375" text-anchor="middle" font-size="10.5" fill="#334155">kitchen (:8201)</text>
          <text x="601" y="394" text-anchor="middle" font-size="10.5" font-weight="600" fill="#b45309">kitchen-db (trọng tài hủy)</text>

          <!-- Row 4: Central Replica & Query -->
          <rect x="336" y="432" width="348" height="72" rx="9" fill="#f1f5f9" stroke="#64748b" stroke-width="1.4"/>
          <text x="510" y="454" text-anchor="middle" font-size="12" font-weight="700" fill="#1e293b">Nhân bản logic &amp; Tổng hợp trung tâm</text>
          <text x="510" y="473" text-anchor="middle" font-size="11" fill="#334155">pos01/pos02/online-db → central-db → query (:8401)</text>
          <text x="510" y="492" text-anchor="middle" font-size="10.5" font-weight="600" fill="#dc2626">Điểm cắt 2: Tách replication-net khỏi central-db</text>

          <!-- Right column: Verified Invariants & Assertions -->
          <rect x="752" y="54" width="272" height="466" rx="12" fill="#f8fafc" stroke="#15803d" stroke-width="1.5"/>
          <text x="888" y="80" text-anchor="middle" font-size="13" font-weight="700" fill="#14532d">TIÊU CHÍ KIỂM CHỨNG</text>

          <rect x="768" y="98" width="240" height="86" rx="8" fill="#ffffff" stroke="#15803d" stroke-width="1.2"/>
          <text x="888" y="119" text-anchor="middle" font-size="12" font-weight="700" fill="#14532d">1. Toàn vẹn đơn ngoại tuyến</text>
          <text x="888" y="138" text-anchor="middle" font-size="11" fill="#334155">Hủy tại quầy trước khi gửi không đẩy</text>
          <text x="888" y="155" text-anchor="middle" font-size="11" fill="#334155">lên Kafka; đơn còn lại tự nối và</text>
          <text x="888" y="172" text-anchor="middle" font-size="11" fill="#334155">giữ kho đủ sau khi khôi phục mạng.</text>

          <rect x="768" y="198" width="240" height="92" rx="8" fill="#ffffff" stroke="#b45309" stroke-width="1.2"/>
          <text x="888" y="219" text-anchor="middle" font-size="12" font-weight="700" fill="#92400e">2. Chịu lỗi tiến trình &amp; Broker</text>
          <text x="888" y="238" text-anchor="middle" font-size="11" fill="#334155">Dừng Kho/Bếp hoặc kill leader Kafka:</text>
          <text x="888" y="255" text-anchor="middle" font-size="11" fill="#334155">0 bản tin mất, chống trùng một lần,</text>
          <text x="888" y="272" text-anchor="middle" font-size="11" fill="#334155">bản tin lỗi tự cô lập sang hàng chờ lỗi.</text>

          <rect x="768" y="302" width="240" height="86" rx="8" fill="#ffffff" stroke="#1d4ed8" stroke-width="1.2"/>
          <text x="888" y="323" text-anchor="middle" font-size="12" font-weight="700" fill="#1e3a8a">3. Chống xung đột tài nguyên</text>
          <text x="888" y="342" text-anchor="middle" font-size="11" fill="#334155">Hai instance Kho giữ cùng nguyên liệu</text>
          <text x="888" y="359" text-anchor="middle" font-size="11" fill="#334155">chỉ 1 đơn thắng; tranh chấp Hủy vs Nấu</text>
          <text x="888" y="376" text-anchor="middle" font-size="11" fill="#334155">nhất quán tuyệt đối ở cả ba dịch vụ.</text>

          <rect x="768" y="404" width="240" height="96" rx="8" fill="#ffffff" stroke="#64748b" stroke-width="1.2"/>
          <text x="888" y="425" text-anchor="middle" font-size="12" font-weight="700" fill="#1e293b">4. Phục hồi nhân bản &amp; Tải 250u</text>
          <text x="888" y="444" text-anchor="middle" font-size="11" fill="#334155">Cắt 1 kênh nhân bản: báo cáo vẫn chạy,</text>
          <text x="888" y="461" text-anchor="middle" font-size="11" fill="#334155">hiện đúng độ trễ và tự khớp khi nối lại.</text>
          <text x="888" y="478" text-anchor="middle" font-size="11" fill="#334155">Tải 250 luồng đạt tỷ lệ lỗi 0,00%.</text>

          <!-- Arrows Connecting Left -> Center -> Right (zero crossing) -->
          <path d="M 244,155 L 334,155" fill="none" stroke="#1d4ed8" stroke-width="1.8" marker-end="url(#tArrB)"/>
          <path d="M 244,291 L 314,291" fill="none" stroke="#dc2626" stroke-width="1.8" stroke-dasharray="5,4" marker-end="url(#tArrR)"/>
          <path d="M 244,436 L 314,436" fill="none" stroke="#15803d" stroke-width="1.8" marker-end="url(#tArrG)"/>

          <path d="M 684,142 L 766,142" fill="none" stroke="#475569" stroke-width="1.6" marker-end="url(#tArrG)"/>
          <path d="M 684,268 L 726,268 L 726,244 L 766,244" fill="none" stroke="#475569" stroke-width="1.6" marker-end="url(#tArrG)"/>
          <path d="M 684,368 L 726,368 L 726,345 L 766,345" fill="none" stroke="#475569" stroke-width="1.6" marker-end="url(#tArrG)"/>
          <path d="M 684,468 L 766,468" fill="none" stroke="#475569" stroke-width="1.6" marker-end="url(#tArrG)"/>

          <!-- Legend -->
          <line x1="18" y1="556" x2="62" y2="556" stroke="#1d4ed8" stroke-width="1.8" marker-end="url(#tArrB)"/>
          <text x="72" y="560" font-size="12" fill="#334155">gửi yêu cầu API &amp; kiểm tra trạng thái CSDL/Kafka</text>

          <line x1="408" y1="556" x2="452" y2="556" stroke="#dc2626" stroke-width="1.8" stroke-dasharray="5,4" marker-end="url(#tArrR)"/>
          <text x="462" y="560" font-size="12" fill="#334155">tiêm lỗi cô lập mạng / dừng tiến trình</text>

          <line x1="744" y1="556" x2="788" y2="556" stroke="#475569" stroke-width="1.6" marker-end="url(#tArrG)"/>
          <text x="798" y="560" font-size="12" fill="#334155">đối chiếu bất biến nghiệp vụ</text>
        </svg>
      </div>
    `,
  },
];
