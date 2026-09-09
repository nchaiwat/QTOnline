# =================================================================================
# [NEW] Customer Document Upload APIs
# =================================================================================

@app.route('/api/pos/<int:id>/upload-location', methods=['POST'])
@login_required
def upload_customer_location(id):
    """
    Upload customer location/map file
    
    Authorization: PO Owner OR Sale Admin OR Administrator
    File Types: PDF, JPG, JPEG, PNG, GIF
    Max Size: 10MB
    """
    po = PurchaseOrder.query.get_or_404(id)
    
    # Authorization check
    if current_user.id != po.sale_user_id and current_user.role not in ['Administrator', 'Sale Admin']:
        return jsonify({"error": "Unauthorized to upload documents for this PO"}), 403
    
    # Validate file
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    # Validate file type
    allowed_extensions = {'pdf', 'jpg', 'jpeg', 'png', 'gif'}
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        return jsonify({"error": "Invalid file type. Allowed: PDF, JPG, PNG, GIF"}), 400
    
    # Validate file size (10MB)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > 10 * 1024 * 1024:
        return jsonify({"error": "File size exceeds 10MB limit"}), 400
    
    try:
        # Delete old file if exists
        if po.customerLocationFile:
            old_path = os.path.join(app.config['UPLOAD_FOLDER'], po.customerLocationFile)
            if os.path.exists(old_path):
                os.remove(old_path)
                app.logger.info(f"Deleted old location file: {po.customerLocationFile}")
        
        # Determine output extension and path
        save_ext = "jpg" if ext in {"jpg", "jpeg", "png", "gif"} else ext
        filename = secure_filename(
            f"location_{po.poNumber}_{int(datetime.now().timestamp())}.{save_ext}"
        )
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Save to temp file first, then compress
        temp_filename = f"temp_{filename}"
        temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
        file.save(temp_filepath)

        from utils import compress_image, compress_pdf
        if save_ext == "pdf":
            compress_pdf(temp_filepath, filepath)
        else:
            compress_image(temp_filepath, filepath)

        # Remove temp file
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        
        # Update database
        po.customerLocationFile = filename
        po.customerLocationFileUrl = f"/uploads/{filename}"
        po.customerLocationUploadedAt = now_bangkok()
        po.customerLocationUploadedBy = current_user.id
        
        # Add comment log
        comment = Comment(
            po_id=po.id,
            user_id=current_user.id,
            user=current_user.fullName,
            text=f"อัปโหลดแผนที่/ตำแหน่งลูกค้า: {file.filename}"
        )
        db.session.add(comment)
        
        db.session.commit()
        
        app.logger.info(f"Location file uploaded: {filename} for PO {po.poNumber} by {current_user.fullName}")
        
        return jsonify({
            "message": "อัปโหลดแผนที่สำเร็จ",
            "fileUrl": po.customerLocationFileUrl,
            "filename": filename
        }), 200
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error uploading location file: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/pos/<int:id>/upload-customer-po', methods=['POST'])
@login_required
def upload_customer_po_file(id):
    """
    Upload customer PO document
    
    Authorization: PO Owner OR Sale Admin OR Administrator
    File Types: PDF, JPG, JPEG, PNG, GIF
    Max Size: 10MB
    """
    po = PurchaseOrder.query.get_or_404(id)
    
    # Authorization check
    if current_user.id != po.sale_user_id and current_user.role not in ['Administrator', 'Sale Admin']:
        return jsonify({"error": "Unauthorized to upload documents for this PO"}), 403
    
    # Validate file
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    # Validate file type
    allowed_extensions = {'pdf', 'jpg', 'jpeg', 'png', 'gif'}
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        return jsonify({"error": "Invalid file type. Allowed: PDF, JPG, PNG, GIF"}), 400
    
    # Validate file size (10MB)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > 10 * 1024 * 1024:
        return jsonify({"error": "File size exceeds 10MB limit"}), 400
    
    try:
        # Delete old file if exists
        if po.customerPoFile:
            old_path = os.path.join(app.config['UPLOAD_FOLDER'], po.customerPoFile)
            if os.path.exists(old_path):
                os.remove(old_path)
                app.logger.info(f"Deleted old customer PO file: {po.customerPoFile}")
        
        # Determine output extension and path
        save_ext = "jpg" if ext in {"jpg", "jpeg", "png", "gif"} else ext
        filename = secure_filename(
            f"customer_po_{po.poNumber}_{int(datetime.now().timestamp())}.{save_ext}"
        )
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Save to temp file first, then compress
        temp_filename = f"temp_{filename}"
        temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
        file.save(temp_filepath)

        from utils import compress_image, compress_pdf
        if save_ext == "pdf":
            compress_pdf(temp_filepath, filepath)
        else:
            compress_image(temp_filepath, filepath)

        # Remove temp file
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        
        # Update database
        po.customerPoFile = filename
        po.customerPoFileUrl = f"/uploads/{filename}"
        po.customerPoUploadedAt = now_bangkok()
        po.customerPoUploadedBy = current_user.id
        
        # Add comment log
        comment = Comment(
            po_id=po.id,
            user_id=current_user.id,
            user=current_user.fullName,
            text=f"อัปโหลด PO ของลูกค้า: {file.filename}"
        )
        db.session.add(comment)
        
        db.session.commit()
        
        app.logger.info(f"Customer PO file uploaded: {filename} for PO {po.poNumber} by {current_user.fullName}")
        
        return jsonify({
            "message": "อัปโหลด PO ลูกค้าสำเร็จ",
            "fileUrl": po.customerPoFileUrl,
            "filename": filename
        }), 200
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error uploading customer PO file: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/pos/<int:id>/delete-location', methods=['DELETE'])
@login_required
def delete_customer_location(id):
    """
    Delete customer location file
    
    Authorization: PO Owner OR Sale Admin OR Administrator
    """
    po = PurchaseOrder.query.get_or_404(id)
    
    # Authorization check
    if current_user.id != po.sale_user_id and current_user.role not in ['Administrator', 'Sale Admin']:
        return jsonify({"error": "Unauthorized to delete documents for this PO"}), 403
    
    if not po.customerLocationFile:
        return jsonify({"error": "No location file to delete"}), 400
    
    try:
        # Delete file from filesystem
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], po.customerLocationFile)
        if os.path.exists(filepath):
            os.remove(filepath)
            app.logger.info(f"Deleted location file: {po.customerLocationFile}")
        
        # Update database
        old_filename = po.customerLocationFile
        po.customerLocationFile = None
        po.customerLocationFileUrl = None
        po.customerLocationUploadedAt = None
        po.customerLocationUploadedBy = None
        
        # Add comment log
        comment = Comment(
            po_id=po.id,
            user_id=current_user.id,
            user=current_user.fullName,
            text=f"ลบแผนที่/ตำแหน่งลูกค้า: {old_filename}"
        )
        db.session.add(comment)
        
        db.session.commit()
        
        app.logger.info(f"Location file deleted for PO {po.poNumber} by {current_user.fullName}")
        
        return jsonify({"message": "ลบไฟล์แผนที่สำเร็จ"}), 200
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting location file: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/pos/<int:id>/delete-customer-po', methods=['DELETE'])
@login_required
def delete_customer_po_file(id):
    """
    Delete customer PO file
    
    Authorization: PO Owner OR Sale Admin OR Administrator
    """
    po = PurchaseOrder.query.get_or_404(id)
    
    # Authorization check
    if current_user.id != po.sale_user_id and current_user.role not in ['Administrator', 'Sale Admin']:
        return jsonify({"error": "Unauthorized to delete documents for this PO"}), 403
    
    if not po.customerPoFile:
        return jsonify({"error": "No customer PO file to delete"}), 400
    
    try:
        # Delete file from filesystem
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], po.customerPoFile)
        if os.path.exists(filepath):
            os.remove(filepath)
            app.logger.info(f"Deleted customer PO file: {po.customerPoFile}")
        
        # Update database
        old_filename = po.customerPoFile
        po.customerPoFile = None
        po.customerPoFileUrl = None
        po.customerPoUploadedAt = None
        po.customerPoUploadedBy = None
        
        # Add comment log
        comment = Comment(
            po_id=po.id,
            user_id=current_user.id,
            user=current_user.fullName,
            text=f"ลบ PO ของลูกค้า: {old_filename}"
        )
        db.session.add(comment)
        
        db.session.commit()
        
        app.logger.info(f"Customer PO file deleted for PO {po.poNumber} by {current_user.fullName}")
        
        return jsonify({"message": "ลบไฟล์ PO ลูกค้าสำเร็จ"}), 200
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting customer PO file: {e}")
        return jsonify({"error": str(e)}), 500
