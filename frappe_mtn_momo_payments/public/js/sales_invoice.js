frappe.ui.form.on('Sales Invoice', {
  refresh(frm) {
    if (frm.is_new()) return;
    frm.add_custom_button(__('MTN MoMo Request Payment'), () => {
      open_mtn_momo_collection_dialog({
        reference_doctype: 'Sales Invoice',
        reference_name: frm.doc.name,
        company: frm.doc.company,
        amount: frm.doc.outstanding_amount || frm.doc.rounded_total || frm.doc.grand_total,
      });
    }, __('Create'));
  }
});

function open_mtn_momo_collection_dialog(opts) {
  frappe.call({
    method: 'frappe_mtn_momo_payments.api.common.get_active_settings',
    args: { company: opts.company },
    callback(r) {
      const s = r.message;
      const d = new frappe.ui.Dialog({
        title: __('MTN MoMo Collection'),
        fields: [
          { fieldname: 'settings', label: __('Settings'), fieldtype: 'Data', default: s.name, read_only: 1 },
          { fieldname: 'phone_number', label: __('Mobile Number'), fieldtype: 'Data', reqd: 1 },
          { fieldname: 'amount', label: __('Amount'), fieldtype: 'Currency', reqd: 1, default: opts.amount },
          { fieldname: 'payer_message', label: __('Payer Message'), fieldtype: 'Data', default: __('ERPNext payment request') },
          { fieldname: 'payee_note', label: __('Payee Note'), fieldtype: 'Data', default: __('MTN MoMo collection') },
        ],
        primary_action_label: __('Send Request'),
        primary_action(values) {
          frappe.call({
            method: 'frappe_mtn_momo_payments.api.collections.request_payment_for_reference',
            args: {
              settings: values.settings,
              reference_doctype: opts.reference_doctype,
              reference_name: opts.reference_name,
              phone_number: values.phone_number,
              amount: values.amount,
              payer_message: values.payer_message,
              payee_note: values.payee_note,
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
}
