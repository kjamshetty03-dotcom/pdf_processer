<template>
  <div class="pdf-manager">
    <div class="header">
      <h1>💼 Payslip Manager</h1>
      <div class="upload-section">
        <input type="file" @change="onFileSelected" accept=".pdf">
        <button @click.prevent.stop="uploadPDF" class="btn-upload">+ Upload Payslip</button>
        <p v-if="uploadStatus" :class="uploadStatus.includes('✓') ? 'success' : 'error'">
          {{ uploadStatus }}
        </p>
      </div>
    </div>

    <div class="content-wrapper">
      <!-- Left Section: Payslip List -->
      <div class="payslip-list-section">
        <h2>My Payslips</h2>
        <div v-if="loading" class="loader">Loading payslips...</div>
        <div v-else-if="pdfs.length === 0" class="no-payslips">No payslips uploaded yet</div>
        <div v-else class="payslip-list">
          <div 
            v-for="pdf in pdfs" 
            :key="pdf.id" 
            class="payslip-item"
            :class="{ active: selectedPdf && selectedPdf.id === pdf.id }"
            @click.prevent.stop="selectPdf(pdf)"
          >
            <div class="payslip-icon">📄</div>
            <div class="payslip-info">
              <p class="payslip-name">{{ pdf.filename }}</p>
              <p class="payslip-date">{{ formatDate(pdf.created_at) }}</p>
            </div>
            <button 
              @click.prevent.stop="deletePDF(pdf)" 
              class="btn-delete"
              title="Delete payslip"
            >
              🗑️
            </button>
          </div>
        </div>
      </div>

      <!-- Right Section: Payslip Preview -->
      <div class="payslip-preview-section">
        <div v-if="!selectedPdf" class="no-selection">
          <div class="empty-state">
            <p>📋</p>
            <h3>No Payslip Selected</h3>
            <p>Select a payslip from the left to view</p>
          </div>
        </div>
        <div v-else class="payslip-container">
          <div class="payslip-page">
            <!-- Payslip Header -->
            <div class="payslip-header-section">
              <div class="header-left">PAYSLIP</div>
              <div class="header-right">{{ employeeName }}</div>
            </div>

            <!-- Payslip Content -->
            <div class="payslip-data">
              <div v-if="extractedKeyValues.length > 0">
                <div v-for="(item, index) in extractedKeyValues" :key="index" class="data-line">
                  <span class="data-key">{{ item.key }}</span>
                  <span class="data-val">{{ item.value }}</span>
                </div>
              </div>
              <div v-else class="raw-content">
                {{ selectedPdf.text_preview }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="showDeleteModal" class="modal-overlay" @click.stop="cancelDelete">
      <div class="modal-content" @click.stop>
        <h3>Delete Payslip</h3>
        <p>Are you sure you want to delete this payslip?</p>
        <p class="modal-filename"><strong>{{ deletingPdf?.filename }}</strong></p>
        <div class="modal-actions">
          <button @click.prevent.stop="cancelDelete" class="btn-cancel">Cancel</button>
          <button @click.prevent.stop="confirmDelete" class="btn-confirm-delete">Delete</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PayslipManager',
  data() {
    return {
      pdfs: [],
      selectedFile: null,
      selectedPdf: null,
      uploadStatus: '',
      loading: true,
      extractedKeyValues: [],
      employeeName: '',
      showDeleteModal: false,
      deletingPdf: null,
      isDeleting: false
    };
  },
  mounted() {
    this.initializeFetch();
  },
  beforeUnmount() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
  },
  methods: {
    formatDate(dateString) {
      if (!dateString) return 'Unknown date';
      const date = new Date(dateString);
      const options = { year: 'numeric', month: 'short', day: 'numeric' };
      return date.toLocaleDateString('en-US', options);
    },
    async initializeFetch() {
      await this.fetchPDFs();
    },
    async fetchPDFs() {
      try {
        this.loading = true;
        
        const response = await fetch('http://localhost:8000/fetch-pdfs', {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'success' && data.documents) {
          this.pdfs = data.documents;
        } else {
          throw new Error('Invalid response format');
        }
        
        this.loading = false;
      } catch (error) {
        console.error('Error fetching payslips:', error);
        this.loading = false;
      }
    },
    extractKeyValues(text) {
      const lines = text.split('\n').filter(line => line.trim());
      const keyValues = [];
      let name = '';
      
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        
        if (line.includes(':')) {
          const [key, value] = line.split(':').map(s => s.trim());
          if (key && value) {
            keyValues.push({ 
              key: this.formatKey(key), 
              value: this.formatValue(value)
            });
            if ((key.toLowerCase().includes('name') || key.toLowerCase().includes('employee')) && !name) {
              name = value;
            }
          }
        }
        else if (i + 1 < lines.length && line.length > 0) {
          const nextLine = lines[i + 1].trim();
          if (nextLine.length > 0 && !nextLine.match(/^[A-Z\s]+$/) && !nextLine.includes(':')) {
            keyValues.push({ 
              key: this.formatKey(line), 
              value: this.formatValue(nextLine)
            });
            if ((line.toLowerCase().includes('name') || line.toLowerCase().includes('employee')) && !name) {
              name = nextLine;
            }
            i++;
          }
        }
      }
      
      this.employeeName = name || 'Employee';
      return keyValues;
    },
    formatKey(key) {
      // Format key: remove underscores, capitalize words
      return key
        .replace(/_/g, ' ')
        .replace(/\b\w/g, char => char.toUpperCase());
    },
    formatValue(value) {
      // Format value: capitalize first letter, handle currency
      let formatted = value.trim();
      
      // Handle currency formats
      if (formatted.match(/^\d+\.?\d*$/)) {
        if (!formatted.includes('.')) {
          formatted = formatted;
        } else {
          formatted = parseFloat(formatted).toFixed(2);
        }
      }
      
      // Capitalize first letter
      if (formatted.length > 0) {
        formatted = formatted.charAt(0).toUpperCase() + formatted.slice(1);
      }
      
      return formatted;
    },
    selectPdf(pdf) {
      this.selectedPdf = pdf;
      this.extractedKeyValues = this.extractKeyValues(pdf.text_preview);
    },
    onFileSelected(event) {
      this.selectedFile = event.target.files[0];
    },
    async uploadPDF(event) {
      event.preventDefault();
      event.stopPropagation();
      
      if (!this.selectedFile) {
        this.uploadStatus = '❌ Please select a file';
        return;
      }

      const formData = new FormData();
      formData.append('file', this.selectedFile);

      try {
        const response = await fetch('http://localhost:8000/upload-pdf', {
          method: 'POST',
          body: formData
        });
        const data = await response.json();
        
        if (data.status === 'success') {
          this.uploadStatus = '✓ Payslip uploaded successfully!';
          this.selectedFile = null;
          document.querySelector('input[type="file"]').value = '';
          setTimeout(() => this.uploadStatus = '', 3000);
          await this.fetchPDFs();
        } else {
          this.uploadStatus = '✗ ' + (data.message || 'Upload failed');
        }
      } catch (error) {
        this.uploadStatus = '✗ Upload failed: ' + error.message;
        console.error('Upload error:', error);
      }
    },
    deletePDF(pdf) {
      this.deletingPdf = pdf;
      this.showDeleteModal = true;
    },
    cancelDelete() {
      this.showDeleteModal = false;
      this.deletingPdf = null;
    },
    async confirmDelete() {
      if (!this.deletingPdf || this.isDeleting) {
        return;
      }

      this.isDeleting = true;

      try {
        const response = await fetch(`http://localhost:8000/delete-pdf/${this.deletingPdf.id}`, {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.status === 'success' || response.ok) {
          this.uploadStatus = '✓ Payslip deleted successfully!';
          
          if (this.selectedPdf && this.selectedPdf.id === this.deletingPdf.id) {
            this.selectedPdf = null;
            this.extractedKeyValues = [];
            this.employeeName = '';
          }
          
          setTimeout(() => this.uploadStatus = '', 3000);
          await this.fetchPDFs();
          this.showDeleteModal = false;
          this.deletingPdf = null;
        } else {
          this.uploadStatus = '✗ ' + (data.message || 'Delete failed');
        }
      } catch (error) {
        this.uploadStatus = '✗ Delete failed: ' + error.message;
        console.error('Delete error:', error);
      } finally {
        this.isDeleting = false;
      }
    }
  }
};
</script>

<style scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.pdf-manager {
  width: 100%;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  font-family: Arial, sans-serif;
}

.header {
  background: white;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  margin-bottom: 30px;
}

.header h1 {
  color: #2c3e50;
  margin-bottom: 20px;
  font-size: 32px;
  font-weight: bold;
}

.upload-section {
  display: flex;
  gap: 15px;
  align-items: center;
}

input[type="file"] {
  padding: 12px 15px;
  border: 2px solid #e8e8e8;
  border-radius: 8px;
  color: #2c3e50;
  font-size: 14px;
  flex: 1;
}

.btn-upload {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 12px 25px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: bold;
  transition: transform 0.2s;
}

.btn-upload:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.success {
  color: #27ae60;
  margin-top: 10px;
  font-weight: bold;
}

.error {
  color: #e74c3c;
  margin-top: 10px;
  font-weight: bold;
}

.content-wrapper {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 30px;
  width: 100%;
}

.payslip-list-section {
  background: white;
  padding: 25px;
  border-radius: 12px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  height: fit-content;
  max-height: 700px;
  overflow-y: auto;
}

.payslip-list-section h2 {
  color: #2c3e50;
  margin-bottom: 20px;
  font-size: 20px;
}

.loader {
  text-align: center;
  padding: 40px 20px;
  color: #95a5a6;
}

.no-payslips {
  text-align: center;
  padding: 60px 20px;
  color: #95a5a6;
}

.payslip-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.payslip-item {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  background: #f8f9fa;
  border: 2px solid #e8e8e8;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.payslip-item:hover {
  background: #f0f0f0;
  border-color: #667eea;
  transform: translateX(5px);
}

.payslip-item.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: #667eea;
}

.payslip-icon {
  font-size: 28px;
  flex-shrink: 0;
}

.payslip-info {
  flex: 1;
}

.payslip-name {
  font-weight: bold;
  color: #2c3e50;
  margin-bottom: 4px;
  word-break: break-word;
  font-size: 14px;
}

.payslip-item.active .payslip-name {
  color: white;
}

.payslip-date {
  font-size: 12px;
  color: #95a5a6;
}

.payslip-item.active .payslip-date {
  color: rgba(255, 255, 255, 0.8);
}

.btn-delete {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 18px;
  padding: 5px 8px;
  border-radius: 5px;
  transition: all 0.2s;
  flex-shrink: 0;
  opacity: 0;
}

.payslip-item:hover .btn-delete {
  opacity: 1;
  background: rgba(231, 76, 60, 0.2);
}

.payslip-item.active .btn-delete {
  opacity: 1;
}

.btn-delete:hover {
  background: rgba(231, 76, 60, 0.4);
  transform: scale(1.1);
}

.payslip-preview-section {
  background: white;
  padding: 0;
  border-radius: 12px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  max-height: 800px;
  overflow-y: auto;
}

.no-selection {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 400px;
}

.empty-state {
  text-align: center;
  color: #95a5a6;
}

.empty-state p:first-child {
  font-size: 64px;
  margin-bottom: 20px;
}

.empty-state h3 {
  color: #2c3e50;
  margin-bottom: 10px;
}

.payslip-container {
  width: 100%;
  padding: 40px;
}

.payslip-page {
  background: white;
  padding: 40px;
  border: 1px solid #ddd;
  min-height: 600px;
}

.payslip-header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  border-bottom: 2px solid #000;
  padding-bottom: 15px;
}

.header-left {
  font-size: 24px;
  font-weight: bold;
  color: #000;
  letter-spacing: 2px;
}

.header-right {
  font-size: 16px;
  font-weight: bold;
  color: #000;
  text-align: right;
}

.payslip-data {
  font-size: 13px;
  line-height: 2;
  color: #333;
}

.data-line {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
}

.data-key {
  font-weight: 600;
  color: #2c3e50;
  min-width: 200px;
}

.data-val {
  color: #34495e;
  text-align: right;
  flex: 1;
  padding-left: 20px;
}

.raw-content {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 2;
  color: #333;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  max-width: 400px;
  width: 90%;
}

.modal-content h3 {
  color: #2c3e50;
  margin-bottom: 15px;
  font-size: 20px;
}

.modal-content p {
  color: #34495e;
  margin-bottom: 10px;
  line-height: 1.6;
}

.modal-filename {
  color: #e74c3c;
  background: #fadbd8;
  padding: 10px;
  border-radius: 5px;
  margin: 15px 0;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 20px;
}

.btn-cancel {
  background: #95a5a6;
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-weight: bold;
  transition: all 0.2s;
}

.btn-cancel:hover {
  background: #7f8c8d;
}

.btn-confirm-delete {
  background: #e74c3c;
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-weight: bold;
  transition: all 0.2s;
}

.btn-confirm-delete:hover {
  background: #c0392b;
}

@media (max-width: 1024px) {
  .content-wrapper {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .header {
    padding: 20px;
  }

  .header h1 {
    font-size: 24px;
  }

  .upload-section {
    flex-direction: column;
  }

  .payslip-container {
    padding: 20px;
  }

  .payslip-page {
    padding: 20px;
  }

  .payslip-header-section {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .data-line {
    flex-direction: column;
  }

  .data-key {
    margin-bottom: 5px;
  }

  .btn-delete {
    opacity: 1;
  }
}
</style>