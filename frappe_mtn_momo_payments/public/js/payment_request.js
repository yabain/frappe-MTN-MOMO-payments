frappe.ui.form.on('Payment Request', {
  refresh(frm) {
    if (frm.is_new()) return;
    frm.add_custom_button(__('Send via MTN MoMo'), () => {
      frappe.call({
        method: 'frappe_mtn_momo_payments.api.common.get_active_settings',
        args: { company: frm.doc.company },
        callback(r) {
          const s = r.message;
          const d = new frappe.ui.Dialog({
            title: __('MTN MoMo Collection'),
            fields: [
              { fieldname: 'settings', label: __('Settings'), fieldtype: 'Data', default: s.name, read_only: 1 },
              { fieldname: 'phone_number', label: __('Mobile Number'), fieldtype: 'Data', reqd: 1 },
              { fieldname: 'amount', label: __('Amount'), fieldtype: 'Currency', reqd: 1, default: frm.doc.grand_total || frm.doc.outstanding_amount },
            ],
            primary_action_label: __('Send Request'),
            primary_action(values) {
              frappe.call({
                method: 'frappe_mtn_momo_payments.api.collections.request_payment_for_reference',
                args: {
                  settings: values.settings,
                  reference_doctype: 'Payment Request',
                  reference_name: frm.doc.name,
                  phone_number: values.phone_number,
                  amount: values.amount,
                },
                freeze: true,
                callback(res) {
                  frappe.msgprint(__('Payment request sent. Transaction: {0}', [res.message.transaction]));
                  d.hide();
                }
              });
            }
          });
          d.show();
        }
      });
    });
  }
});
