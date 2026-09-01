# ─── State: Owner Reset Balance - User ID (continued) ───
    if state == "owner_reset_balance_user":
        try:
            target_id = int(text)
        except:
            await update.message.reply_text(t(user_id, "invalid_user_id_number"), reply_markup=go_back(user_id, "owner"))
            return
        
        conn = get_db()
        target_user = conn.execute("SELECT * FROM users WHERE id = ?", (target_id,)).fetchone()
        if not target_user:
            conn.close()
            await update.message.reply_text(t(user_id, "user_not_found"), reply_markup=go_back(user_id, "owner"))
            return
        
        conn.execute("UPDATE users SET balance = 0 WHERE id = ?", (target_id,))
        conn.commit()
        conn.close()
        
        user_states.pop(user_id, None)
        try:
            await context.bot.send_message(
                target_id,
                t(target_id, "balance_reset_msg")
            )
        except Exception as e:
            print(f"⚠️ Could not notify user about balance reset: {e}")
        
        await update.message.reply_text(
            f"✅ باڵانسی بەکارهێنەر <code>{target_id}</code> کرایەوە بە سفر.",
            parse_mode="HTML",
            reply_markup=owner_balance_menu_kb(user_id)
        )
        return

    # ── State: Owner Add Balance - Amount ──
    if state == "owner_add_balance_amount":
        try:
            amount = int(text.replace(",", ""))
        except:
            await update.message.reply_text(t(user_id, "invalid_amount"), reply_markup=go_back(user_id, "owner"))
            return
        
        target_id = data.get('target_id')
        op_type = data.get('type', 'add')
        
        conn = get_db()
        if op_type == 'add':
            conn.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, target_id))
        else:
            conn.execute("UPDATE users SET balance = ? WHERE id = ?", (amount, target_id))
        conn.commit()
        
        new_bal = conn.execute("SELECT balance FROM users WHERE id = ?", (target_id,)).fetchone()['balance']
        conn.close()
        
        user_states.pop(user_id, None)
        
        try:
            await context.bot.send_message(
                target_id,
                f"🎉 باڵانسەکەت نوێکرایەوە!\n💰 باڵانسی ئێستات: <b>{new_bal:,} دینار</b>",
                parse_mode="HTML"
            )
        except:
            pass
        
        await update.message.reply_text(
            f"✅ بڕی {amount:,} دینار سەرکەوتووانە زیاد کرا بۆ بەکارهێنەر <code>{target_id}</code>.\n\n💰 باڵانسی گشتی: <b>{new_bal:,} دینار</b>",
            parse_mode="HTML",
            reply_markup=owner_balance_menu_kb(user_id)
        )
        return

    # ── State: Owner Set Balance - Amount ──
    if state == "owner_set_balance_amount":
        try:
            new_balance = int(text.replace(",", ""))
        except:
            await update.message.reply_text(t(user_id, "invalid_amount"), reply_markup=go_back(user_id, "owner"))
            return

        target_id = data.get('target_id')
        conn = get_db()
        conn.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, target_id))
        conn.commit()
        conn.close()

        user_states.pop(user_id, None)

        try:
            await context.bot.send_message(
                target_id,
                f"✏️ باڵانسەکەت گۆڕدرا!\n💰 باڵانسی ئێستات: <b>{new_balance:,} دینار</b>",
                parse_mode="HTML"
            )
        except:
            pass

        await update.message.reply_text(
            f"✅ باڵانسی بەکارهێنەر <code>{target_id}</code> کرا بە <b>{new_balance:,} دینار</b>.",
            parse_mode="HTML",
            reply_markup=owner_balance_menu_kb(user_id)
        )
        return

    # ── State: Owner Broadcast ──
    if state == "owner_broadcast":
        msg_text = update.message.text
        user_states.pop(user_id, None)
        
        conn = get_db()
        users = conn.execute("SELECT id FROM users").fetchall()
        conn.close()
        
        sent_count = 0
        fail_count = 0
        
        status_msg = await update.message.reply_text("📢 نامەکە دەنێردرێت بۆ هەموو بەکارهێنەرەکان...")
        
        for u in users:
            try:
                await context.bot.send_message(u['id'], msg_text, parse_mode="HTML")
                sent_count += 1
                await asyncio.sleep(0.05)  # Prevent flood wait
            except:
                fail_count += 1
        
        await status_msg.edit_text(
            f"✅ نامەکە نێردرا!\n\n"
            f"📤 سەرکەوتوو: {sent_count}\n"
            f"❌ سەرنەکەوتوو: {fail_count}",
            reply_markup=owner_main_menu(user_id)
        )
        return

    # Default fallback for unhandled text
    await update.message.reply_text(t(user_id, "not_understood"), reply_markup=user_main_menu(user_id))

# ─── CALLBACK QUERY HANDLER ──────────────────────────────────────────────
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all inline button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username = query.from_user.username or ""
    first_name = query.from_user.first_name or ""
    
    ensure_user(user_id, username, first_name)
    data = query.data
    
    # ── ACTIVATION GATE: unapproved users can only request activation ──
    if not is_owner(user_id) and not is_approved(user_id):
        if data == "request_activation":
            try:
                await context.bot.send_message(
                    OWNER_ID,
                    f"📨 <b>داواکاریی نوێ بۆ ئەکتیڤکردن!</b>\n\n👤 ناو: {html.escape(first_name)}\n🆔 ئایدی: <code>{user_id}</code>\nuser: @{html.escape(username)}",
                    parse_mode="HTML",
                    reply_markup=owner_approval_kb(user_id)
                )
                await query.edit_message_text(
                    "✅ داواکارییەکەت بە سەرکەوتوویی نێردرا بۆ مام زاگرۆس.\n\nتکایە چاوەڕێ بکە تاوەکو ئەکتیڤت دەکات.",
                    reply_markup=approval_request_kb()
                )
            except Exception as e:
                await query.edit_message_text(f"❌ کێشەیەک ڕوویدا: {e}", reply_markup=approval_request_kb())
            return
        else:
            try:
                await query.edit_message_text(
                    "⛔ ئەم بۆتە بۆ تۆ بەردەست نییە.\n\nتکایە کلیک لە «داواکاریی ڕاستەوخۆ» بکە بۆ ئەکتیڤکردن.",
                    reply_markup=approval_request_kb()
                )
            except:
                pass
            return

    # Clear state on navigation
    if data in ("main_menu", "owner_main", "user_account", "user_send_report", "report_control_list"):
        user_states.pop(user_id, None)
    
    # ── Owner Approval Callbacks ──
    if data.startswith("approve_user_") and is_owner(user_id):
        target_id = int(data.split("_")[2])
        set_approved(target_id, 1)
        try:
            await context.bot.send_message(target_id, "✅ پیرۆزە! داواکارییەکەت قبوڵ کرا و بۆتەکە بۆت چالاک بوو. /start بنووسە.")
        except:
            pass
        await query.edit_message_text(f"✅ بەکارهێنەر <code>{target_id}</code> ئەکتیڤ کرا.", parse_mode="HTML")
        return

    if data.startswith("reject_user_") and is_owner(user_id):
        target_id = int(data.split("_")[2])
        try:
            await context.bot.send_message(target_id, "❌ مخابن، داواکارییەکەت ڕەتکرایەوە.")
        except:
            pass
        await query.edit_message_text(f"❌ داواکاریی بەکارهێنەر <code>{target_id}</code> ڕەتکرایەوە.", parse_mode="HTML")
        return

    # ── Main Menu / Start ──
    if data == "main_menu" or data == "user_home":
        if is_owner(user_id):
            await query.edit_message_text(
                t(user_id, "owner_welcome", name=html.escape(first_name)),
                parse_mode="HTML",
                reply_markup=owner_main_menu(user_id)
            )
        else:
            await query.edit_message_text(
                t(user_id, "user_welcome_back", name=html.escape(first_name)),
                parse_mode="HTML",
                reply_markup=user_main_menu(user_id)
            )
        return
    
    if data == "owner_main":
        if is_owner(user_id):
            await query.edit_message_text(
                t(user_id, "owner_welcome", name=html.escape(first_name)),
                parse_mode="HTML",
                reply_markup=owner_main_menu(user_id)
            )
        return

    # ── User: Send Report ──
    if data == "user_send_report":
        if not is_registered(user_id):
            await query.edit_message_text(t(user_id, "not_registered"), reply_markup=back_menu(user_id))
            return
        
        # Check session validity before proceeding
        valid = await check_user_session(user_id)
        if not valid:
            await query.edit_message_text(
                t(user_id, "session_renew_msg"),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 نوێکردنەوەی سێشن", callback_data="register_start")],
                    [InlineKeyboardButton(t(user_id, "back"), callback_data="main_menu")]
                ])
            )
            return
        
        user_states[user_id] = {'state': 'report_link', 'data': {}}
        await query.edit_message_text(
            t(user_id, "enter_link_short"),
            parse_mode="HTML",
            reply_markup=back_menu(user_id)
        )
        return

    # ── User: Account / Balance ──
    if data == "user_account":
        balance = get_user_balance(user_id)
        total_spent = get_user_total_spent(user_id)
        text = (
            f"👤 <b>هەژمارەکەم</b>\n\n"
            f"🆔 ئایدی: <code>{user_id}</code>\n"
            f"💰 باڵانسی ئێستا: <b>{balance:,} دینار</b>\n"
            f"📤 کۆی خەرجکراو: <b>{total_spent:,} دینار</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=balance_menu_user(user_id)
        )
        return

    if data == "balance_topup":
        balance = get_user_balance(user_id)
        await query.edit_message_text(
            t(user_id, "top_up_message", balance=balance, uid=user_id),
            parse_mode="HTML",
            reply_markup=balance_menu_user(user_id)
        )
        return

    # ── Reason Selection & Pricing Flow (User) ──
    if data.startswith("reason_"):
        reason_key = data.split("_")[1]
        user_states[user_id]['data']['report_type'] = reason_key
        
        await query.edit_message_text(
            t(user_id, "select_report_count"),
            parse_mode="HTML",
            reply_markup=pricing_menu(user_id)
        )
        return

    if data.startswith("price_"):
        price_type = data.split("_")[1]
        if price_type == "100":
            count, cost = 100, PRICES[100]
        elif price_type == "500":
            count, cost = 500, PRICES[500]
        elif price_type == "1000":
            count, cost = 1000, PRICES[1000]
        elif price_type == "endless":
            count, cost = -1, PRICES[-1]
        else:
            return
        
        balance = get_user_balance(user_id)
        if balance < cost:
            await query.edit_message_text(
                f"⚠️ <b>باڵانسی پێویستت نییە!</b>\n\nنرخ: <b>{cost:,} دینار</b>\nباڵانسی ئێستات: <b>{balance:,} دینار</b>\n\nتکایە باڵانسەکەت پڕ بکەرەوە.",
                parse_mode="HTML",
                reply_markup=balance_menu_user(user_id)
            )
            return
        
        # Deduct balance immediately
        update_balance(user_id, -cost)
        
        d = user_states.get(user_id, {}).get('data', {})
        link = d.get('report_link', '')
        rtype = d.get('report_type', 'spam')
        
        # Create pending request for owner approval
        conn = get_db()
        cursor = conn.execute(
            "INSERT INTO pending_requests (user_id, report_count, report_type, target_link, price, status) VALUES (?, ?, ?, ?, ?, 'pending')",
            (user_id, count, rtype, link, cost)
        )
        req_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Notify owner
        try:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=(
                    f"🔔 <b>داواکاریی نوێ بۆ ڕیپۆرت!</b>\n\n"
                    f"🆔 ئایدی بەکارهێنەر: <code>{user_id}</code>\n"
                    f"🔗 لینک: <code>{html.escape(link)}</code>\n"
                    f"📊 ژمارە: {count if count > 0 else 'تاکو داخستن'}\n"
                    f"🏷️ جۆر: {rtype}\n"
                    f"💰 نرخ: {cost:,} دینار\n"
                    f"━━━━━━━━━━━━━━━━━━━━"
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ قبوڵکردن و دەستپێکردن", callback_data=f"owner_accept_{req_id}"),
                     InlineKeyboardButton("❌ ڕەتکردنەوە", callback_data=f"owner_reject_{req_id}")]
                ])
            )
        except Exception as e:
            print(f"⚠️ Failed to notify owner about report request: {e}")
        
        user_states.pop(user_id, None)
        await query.edit_message_text(
            t(user_id, "request_submitted"),
            reply_markup=user_main_menu(user_id)
        )
        return

    # ── Owner: Send Report Flow ──
    if data == "owner_send_report" and is_owner(user_id):
        user_states[user_id] = {'state': 'owner_report_link', 'data': {}}
        await query.edit_message_text(
            "📤 <b>بەڕێوەبەر - ناردنی ڕیپۆرت</b>\n\nتکایە لینکی چەناڵ/گرووپ یان پۆست بنێرە:",
            parse_mode="HTML",
            reply_markup=back_menu(user_id, "owner")
        )
        return

    if data.startswith("owner_report_count_") and is_owner(user_id):
        c_type = data.split("_")[3]
        if c_type == "100": count = 100
        elif c_type == "500": count = 500
        elif c_type == "1000": count = 1000
        elif c_type == "endless": count = -1
        else: count = 100
        
        d = user_states.get(user_id, {}).get('data', {})
        link = d.get('report_link', '')
        
        user_states.pop(user_id, None)
        
        # Create control record & start immediately for owner
        conn = get_db()
        cursor = conn.execute(
            "INSERT INTO report_control (request_id, user_id, report_name, status, target_link, report_type, report_count) VALUES (0, ?, ?, 'running', ?, 'hybrid', ?)",
            (user_id, link, link, count)
        )
        rc_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        await query.edit_message_text(
            f"✅ ڕاپۆرتەکە بۆ سەرۆک قبوڵ کرا و دەستی پێکرد! (ئایدی کنترل: {rc_id})",
            reply_markup=owner_main_menu(user_id)
        )
        
        asyncio.create_task(
            send_reports_core(
                link=link,
                rtype='hybrid',
                max_reports=count,
                query=query,
                user_id=user_id,
                report_control_id=rc_id
            )
        )
        return

    # ── Owner: Accept/Reject User Report Requests ──
    if data.startswith("owner_accept_") and is_owner(user_id):
        req_id = int(data.split("_")[2])
        conn = get_db()
        req = conn.execute("SELECT * FROM pending_requests WHERE id = ? AND status = 'pending'", (req_id,)).fetchone()
        if not req:
            conn.close()
            await query.answer("❌ ئەم داواکارییە پێشتر یەکلایی کراوەتەوە.", show_alert=True)
            return
        
        conn.execute("UPDATE pending_requests SET status = 'accepted' WHERE id = ?", (req_id,))
        conn.commit()
        
        # Create report control entry
        cursor = conn.execute(
            "INSERT INTO report_control (request_id, user_id, report_name, status, target_link, report_type, report_count) VALUES (?, ?, ?, 'running', ?, ?, ?)",
            (req_id, req['user_id'], req['target_link'], req['target_link'], req['report_type'], req['report_count'])
        )
        rc_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Notify user
        try:
            await context.bot.send_message(req['user_id'], t(req['user_id'], "request_accepted_user"))
        except:
            pass
        
        await query.edit_message_text(
            f"✅ <b>داواکارییەک قبوڵ کرا و ڕیپۆرت دەستی پێکرد!</b>\n\n🆔 داواکاری: {req_id}\n👤 بەکارهێنەر: <code>{req['user_id']}</code>\n🔗 لینک: <code>{req['target_link']}</code>",
            parse_mode="HTML"
        )
        
        # Start core report task in background
        asyncio.create_task(
            send_reports_core(
                link=req['target_link'],
                rtype=req['report_type'],
                max_reports=req['report_count'],
                query=query,
                user_id=req['user_id'],
                report_control_id=rc_id
            )
        )
        return

    if data.startswith("owner_reject_") and is_owner(user_id):
        req_id = int(data.split("_")[2])
        conn = get_db()
        req = conn.execute("SELECT * FROM pending_requests WHERE id = ? AND status = 'pending'", (req_id,)).fetchone()
        if not req:
            conn.close()
            await query.answer("❌ ئەم داواکارییە پێشتر یەکلایی کراوەتەوە.", show_alert=True)
            return
        
        conn.execute("UPDATE pending_requests SET status = 'rejected' WHERE id = ?", (req_id,))
        # Refund user balance
        conn.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (req['price'], req['user_id']))
        conn.commit()
        conn.close()
        
        # Notify user
        try:
            await context.bot.send_message(
                req['user_id'],
                t(req['user_id'], "request_rejected_user", price=req['price'])
            )
        except:
            pass
        
        await query.edit_message_text(
            f"❌ <b>داواکاری ڕەتکرایەوە و پارە بۆ بەکارهێنەر گەڕێندرایەوە.</b>\n\n🆔 داواکاری: {req_id}",
            parse_mode="HTML"
        )
        return

    # ── Report Control Center (Pause/Resume/Delete) ──
    if data == "report_control_list":
        conn = get_db()
        controls = conn.execute("SELECT * FROM report_control WHERE status != 'stopped'").fetchall()
        conn.close()
        
        if not controls:
            await query.edit_message_text(
                t(user_id, "report_control_empty"),
                parse_mode="HTML",
                reply_markup=back_menu(user_id, "owner" if is_owner(user_id) else "user")
            )
            return
        
        kb = []
        for rc in controls:
            status_icon = "▶️" if rc['status'] == 'running' else "⏸"
            kb.append([InlineKeyboardButton(f"{status_icon} {rc['target_link']} ({rc['success_count']}/{rc['report_count'] if rc['report_count']>0 else '∞'})", callback_data=f"rc_manage_{rc['id']}")])
        
        kb.append([InlineKeyboardButton(t(user_id, "back"), callback_data="owner_main" if is_owner(user_id) else "main_menu")])
        
        await query.edit_message_text(
            t(user_id, "report_control_select"),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    if data.startswith("rc_manage_"):
        rc_id = int(data.split("_")[2])
        conn = get_db()
        rc = conn.execute("SELECT * FROM report_control WHERE id = ?", (rc_id,)).fetchone()
        conn.close()
        
        if not rc:
            await query.answer("❌ ڕیپۆرتەکە نەدۆزرایەوە.", show_alert=True)
            return
        
        is_running = (rc['status'] == 'running')
        toggle_text = t(user_id, "stop_report") if is_running else t(user_id, "continue_report")
        toggle_action = f"rc_toggle_{rc_id}"
        
        text = (
            f"📊 <b>بەڕێوەبردنی ڕیپۆرت</b>\n\n"
            f"🔗 لینک: <code>{html.escape(rc['target_link'])}</code>\n"
            f"🏷️ جۆر: {rc['report_type']}\n"
            f"📊 دۆخ: <b>{rc['status']}</b>\n"
            f"✅ سەرکەوتوو: {rc['success_count']}\n"
            f"❌ شکست: {rc['fail_count']}\n"
            f"📈 پێشکەوتن: {rc['success_count'] + rc['fail_count']}/{rc['report_count'] if rc['report_count']>0 else '∞'}"
        )
        
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(toggle_text, callback_data=toggle_action),
                 InlineKeyboardButton(t(user_id, "delete_report"), callback_data=f"rc_delete_{rc_id}")],
                [InlineKeyboardButton(t(user_id, "back"), callback_data="report_control_list")]
            ])
        )
        return

    if data.startswith("rc_toggle_"):
        rc_id = int(data.split("_")[2])
        conn = get_db()
        rc = conn.execute("SELECT * FROM report_control WHERE id = ?", (rc_id,)).fetchone()
        if rc:
            new_status = 'paused' if rc['status'] == 'running' else 'running'
            conn.execute("UPDATE report_control SET status = ? WHERE id = ?", (new_status, rc_id))
            conn.commit()
        conn.close()
        
        # Refresh management view
        query.data = f"rc_manage_{rc_id}"
        return await handle_callback_query(update, context)

    if data.startswith("rc_delete_"):
        rc_id = int(data.split("_")[2])
        conn = get_db()
        conn.execute("UPDATE report_control SET status = 'stopped' WHERE id = ?", (rc_id,))
        conn.execute("DELETE FROM report_control WHERE id = ?", (rc_id,))
        conn.commit()
        conn.close()
        
        # Cancel running task if any
        if rc_id in active_report_tasks:
            task = active_report_tasks.pop(rc_id, None)
            if task:
                task.cancel()
        
        await query.answer("🗑️ ڕیپۆرتەکە سڕایەوە و وەستا.", show_alert=True)
        query.data = "report_control_list"
        return await handle_callback_query(update, context)

    # ── Owner: Sections Management ──
    if data == "owner_sections" and is_owner(user_id):
        await query.edit_message_text(
            t(user_id, "owner_sections_menu"),
            parse_mode="HTML",
            reply_markup=owner_sections_menu_kb(user_id)
        )
        return

    if data == "owner_view_sections" and is_owner(user_id):
        conn = get_db()
        sections = conn.execute("SELECT * FROM sections").fetchall()
        conn.close()
        
        if not sections:
            await query.edit_message_text(
                t(user_id, "no_sections_owner"),
                reply_markup=owner_sections_menu_kb(user_id)
            )
            return
        
        text = "📋 <b>لیستی سێکشنەکان:</b>\n\n"
        kb = []
        for s in sections:
            status_icon = "🟢" if s['status'] == 'active' else "🔴"
            text += f"{status_icon} <b>{html.escape(s['name'])}</b>\n📱 <code>{s['phone']}</code>\n\n"
            kb.append([
                InlineKeyboardButton(f"⚙️ {s['name']}", callback_data=f"sec_info_{s['id']}"),
                InlineKeyboardButton("🗑️", callback_data=f"sec_del_{s['id']}")
            ])
        
        kb.append([InlineKeyboardButton(t(user_id, "back"), callback_data="owner_sections")])
        
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("sec_info_") and is_owner(user_id):
        sec_id = int(data.split("_")[2])
        conn = get_db()
        s = conn.execute("SELECT * FROM sections WHERE id = ?", (sec_id,)).fetchone()
        conn.close()
        
        if not s:
            await query.answer("❌ سێکشن نەدۆزرایەوە.", show_alert=True)
            return
        
        text = (
            f"📌 <b>زانیاریی سێکشن:</b>\n\n"
            f"📝 ناو: {html.escape(s['name'])}\n"
            f"📱 ژمارە: <code>{s['phone']}</code>\n"
            f"🟢 دۆخ: {s['status']}\n"
            f"🌐 پڕۆکسی: <code>{s['proxy'] or 'بێ پڕۆکسی'}</code>\n"
            f"🔑 سێشن: <code>{s['session_string'][:30]}...</code>"
        )
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 گۆڕینی دۆخ (Active/Inactive)", callback_data=f"sec_toggle_status_{s['id']}")],
                [InlineKeyboardButton("🌐 دانانی پڕۆکسی", callback_data=f"sec_set_proxy_{s['id']}")],
                [InlineKeyboardButton(t(user_id, "back"), callback_data="owner_view_sections")]
            ])
        )
        return

    if data.startswith("sec_toggle_status_") and is_owner(user_id):
        sec_id = int(data.split("_")[3])
        conn = get_db()
        s = conn.execute("SELECT * FROM sections WHERE id = ?", (sec_id,)).fetchone()
        if s:
            new_status = 'inactive' if s['status'] == 'active' else 'active'
            conn.execute("UPDATE sections SET status = ? WHERE id = ?", (new_status, sec_id))
            conn.commit()
        conn.close()
        query.data = f"sec_info_{sec_id}"
        return await handle_callback_query(update, context)

    if data.startswith("sec_set_proxy_") and is_owner(user_id):
        sec_id = int(data.split("_")[3])
        user_states[user_id] = {'state': 'waiting_for_proxy', 'data': {'section_id': sec_id}}
        await query.edit_message_text(
            "🌐 تکایە پڕۆکسی نوێ بنووسە بەم فۆرماتە:\n\n<code>type:ip:port:username:password</code>\n\nیان بنووسە <code>none</code> بۆ لابردنی پڕۆکسی.",
            parse_mode="HTML",
            reply_markup=owner_sections_menu_kb(user_id)
        )
        return

    if data.startswith("sec_del_") and is_owner(user_id):
        sec_id = int(data.split("_")[2])
        conn = get_db()
        conn.execute("DELETE FROM sections WHERE id = ?", (sec_id,))
        conn.commit()
        conn.close()
        await query.answer("🗑️ سێکشنەکە سڕایەوە.", show_alert=True)
        query.data = "owner_view_sections"
        return await handle_callback_query(update, context)

    if data == "owner_add_section" and is_owner(user_id):
        await query.edit_message_text(
            t(user_id, "add_section_prompt"),
            parse_mode="HTML",
            reply_markup=owner_add_section_kb(user_id)
        )
        return

    if data == "owner_add_by_phone" and is_owner(user_id):
        user_states[user_id] = {'state': 'owner_add_phone', 'data': {}}
        await query.edit_message_text(
            t(user_id, "enter_phone_section"),
            parse_mode="HTML",
            reply_markup=owner_sections_menu_kb(user_id)
        )
        return

    if data == "owner_add_by_code" and is_owner(user_id):
        user_states[user_id] = {'state': 'owner_add_session', 'data': {}}
        await query.edit_message_text(
            t(user_id, "enter_session_code"),
            parse_mode="HTML",
            reply_markup=owner_sections_menu_kb(user_id)
        )
        return

    if data.startswith("add_proxy_after_") and is_owner(user_id):
        sec_id = int(data.split("_")[3])
        user_states[user_id] = {'state': 'waiting_for_proxy', 'data': {'section_id': sec_id}}
        await query.edit_message_text(
            "🌐 تکایە پڕۆکسی بنووسە بەم فۆرماتە:\n\n<code>type:ip:port:username:password</code>",
            parse_mode="HTML",
            reply_markup=owner_sections_menu_kb(user_id)
        )
        return

    if data == "skip_proxy_after" and is_owner(user_id):
        user_states.pop(user_id, None)
        await query.edit_message_text(
            "✅ سێکشنەکە بە سەرکەوتوویی زیاد کرا بەبێ پڕۆکسی.",
            reply_markup=owner_sections_menu_kb(user_id)
        )
        return

    # ── Owner: Balance Menu & Actions ──
    if data == "owner_balance_menu" and is_owner(user_id):
        await query.edit_message_text(
            t(user_id, "owner_balance_menu"),
            parse_mode="HTML",
            reply_markup=owner_balance_menu_kb(user_id)
        )
        return

    if data == "owner_add_balance" and is_owner(user_id):
        user_states[user_id] = {'state': 'owner_add_balance_user', 'data': {}}
        await query.edit_message_text(
            t(user_id, "enter_user_id_balance"),
            parse_mode="HTML",
            reply_markup=owner_balance_menu_kb(user_id)
        )
        return

    if data == "owner_set_balance" and is_owner(user_id):
        user_states[user_id] = {'state': 'owner_set_balance_user', 'data': {}}
        await query.edit_message_text(
            "👤 تکایە ئایدی بەکارهێنەر بنووسە بۆ گۆڕینی باڵانسەکەی:",
            parse_mode="HTML",
            reply_markup=owner_balance_menu_kb(user_id)
        )
        return

    if data == "owner_reset_balance" and is_owner(user_id):
        user_states[user_id] = {'state': 'owner_reset_balance_user', 'data': {}}
        await query.edit_message_text(
            "👤 تکایە ئایدی بەکارهێنەر بنووسە بۆ سفرکردنەوەی باڵانسەکەی:",
            parse_mode="HTML",
            reply_markup=owner_balance_menu_kb(user_id)
        )
        return

    if data == "owner_activate_user" and is_owner(user_id):
        user_states[user_id] = {'state': 'owner_activate_user_id', 'data': {}}
        await query.edit_message_text(
            "👤 تکایە ئایدی بەکارهێنەر بنووسە بۆ ئەکتیڤکردن:",
            parse_mode="HTML",
            reply_markup=owner_balance_menu_kb(user_id)
        )
        return

    if data == "owner_delete_user" and is_owner(user_id):
        user_states[user_id] = {'state': 'owner_delete_user_id', 'data': {}}
        await query.edit_message_text(
            "👤 تکایە ئایدی بەکارهێنەر بنووسە بۆ سڕینەوەی دستگەیشتنی:",
            parse_mode="HTML",
            reply_markup=owner_balance_menu_kb(user_id)
        )
        return

    if data == "owner_list_users" and is_owner(user_id):
        conn = get_db()
        users = conn.execute("SELECT id, first_name, username, balance, approved FROM users").fetchall()
        conn.close()
        
        text = "👥 <b>لیستی هەموو بەکارهێنەران:</b>\n\n"
        for u in users:
            status = "🟢" if u['approved'] else "🔴"
            text += f"{status} <b>{html.escape(u['first_name'] or 'None')}</b>\n🆔 <code>{u['id']}</code> | 💰 {u['balance']:,} د\n\n"
        
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=owner_balance_menu_kb(user_id)
        )
        return

    if data == "owner_settings" and is_owner(user_id):
        await query.edit_message_text(
            t(user_id, "settings_menu"),
            parse_mode="HTML",
            reply_markup=owner_settings_kb(user_id)
        )
        return

    if data == "owner_broadcast" and is_owner(user_id):
        user_states[user_id] = {'state': 'owner_broadcast', 'data': {}}
        await query.edit_message_text(
            t(user_id, "enter_broadcast"),
            parse_mode="HTML",
            reply_markup=owner_main_menu(user_id)
        )
        return

# ─── START COMMAND ───────────────────────────────────────────────────────
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    username = update.effective_user.username or ""
    first_name = update.effective_user.first_name or ""
    
    ensure_user(user_id, username, first_name)
    user_states.pop(user_id, None)
    
    # Check activation status
    if not is_owner(user_id) and not is_approved(user_id):
        await update.message.reply_text(
            "⛔ ئەم بۆتە بۆ تۆ بەردەست نییە.\n\nداواکاریی ئەکتیڤکردن بنێرە بۆ مام زاگرۆس @X_MAM6\n\nئایدی بەکارهێنەر: " + str(user_id),
            reply_markup=approval_request_kb()
        )
        return
    
    if is_owner(user_id):
        await update.message.reply_text(
            t(user_id, "owner_welcome", name=html.escape(first_name)),
            parse_mode="HTML",
            reply_markup=owner_main_menu(user_id)
        )
    else:
        await update.message.reply_text(
            t(user_id, "user_welcome_back", name=html.escape(first_name)),
            parse_mode="HTML",
            reply_markup=user_main_menu(user_id)
        )

# ─── MAIN APP ENTRYPOINT ─────────────────────────────────────────────────
def main():
    """Start the bot."""
    if not BOT_TOKEN:
        print("[-] ERROR: BOT_TOKEN environment variable is not set!")
        return
    
    init_db()
    
    # Create application with increased connection pool limits for heavy concurrent reporting
    request = HTTPXRequest(connection_pool_size=100, read_timeout=30.0, write_timeout=30.0, connect_timeout=30.0)
    application = Application.builder().token(BOT_TOKEN).request(request).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    print("[+] Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
