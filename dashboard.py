"""
Streamlit Dashboard - Enterprise Edition
Mobile-friendly demo dashboard with real-time RAG integration
"""

import streamlit as st
import requests
import json
import time
from datetime import datetime
from typing import Dict, List

# Configure Streamlit for mobile-friendly display
st.set_page_config(
    page_title="Parts RAG Demo Dash",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/seanmcdonnell/parts-dist-rag',
        'Report a bug': "https://github.com/seanmcdonnell/parts-dist-rag/issues",
        'About': "Parts RAG Demo - Enterprise AI for Dealerships"
    }
)

# API Configuration
API_BASE_URL = "http://localhost:8000"
EMAIL_API_URL = f"{API_BASE_URL}/process_email"
QUERY_API_URL = f"{API_BASE_URL}/query_parts"
LOGS_API_URL = f"{API_BASE_URL}/logs/recent"

# Import analytics engine
import sys
sys.path.append('.')
from analytics import generate_metrics, get_trend_data

# Import pandas for CSV export
import pandas as pd
from io import StringIO

# Custom CSS for mobile optimization
st.markdown("""
<style>
    /* Mobile-first responsive design */
    @media (max-width: 600px) {
        .main { 
            padding: 0.5rem !important; 
        }
        .stButton > button { 
            height: 3rem !important; 
            font-size: 1.2rem !important; 
            width: 100% !important; 
        }
        h1 { 
            font-size: 1.8rem !important; 
            text-align: center !important;
        }
        h2 { 
            font-size: 1.4rem !important; 
        }
        .stSelectbox > div > div { 
            font-size: 1.1rem !important; 
        }
        .stTextInput > div > div > input { 
            font-size: 1.1rem !important; 
        }
    }
    
    /* Color-coded alerts */
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.375rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 0.375rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .alert-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.375rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    /* Mobile-friendly metrics */
    .metric-container {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    
    @media (min-width: 768px) {
        .metric-container {
            flex-direction: row;
            gap: 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div style="text-align: center; padding: 1rem 0;">
    <h1 style="color: #1f77b4; margin-bottom: 0.5rem;">🛠️ Chicago Dealership Parts AI</h1>
    <p style="color: #666; font-size: 1.1rem;">Lester's Enhanced RAG System - Live Demo</p>
</div>
""", unsafe_allow_html=True)

# Sidebar for controls
with st.sidebar:
    st.header("🎯 Demo Controls")
    
    # Real-time analytics metrics
    st.subheader("📊 Live Metrics")
    try:
        metrics = generate_metrics()
        
        # Key metrics display
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Green Rate", metrics['session_summary']['green_automation_rate'])
            st.metric("Total Queries", metrics['session_summary']['total_queries'])
        with col2:
            st.metric("Savings", metrics['performance_metrics']['total_savings_demo'])
            st.metric("ROI Timeline", f"{metrics['roi_projections']['roi_timeline_months']}m")
        
        # Annual projection
        st.success(f"💰 Annual Projected: {metrics['roi_projections']['annual_savings_projected']}")
        
        # Payment metrics
        if metrics['payment_metrics']['total_payments'] > 0:
            st.info(f"💳 Payments: {metrics['payment_metrics']['total_payments']} ({metrics['payment_metrics']['payment_rate']})")
        
    except Exception as e:
        st.error("Analytics unavailable")
    
    st.markdown("---")
    
    # Demo mode selection
    demo_mode = st.radio(
        "Demo Mode:",
        ["Parts Query", "Email Processing", "System Status"],
        help="Choose your demo scenario"
    )
    
    if demo_mode == "Parts Query":
        st.subheader("Quick Query")
        query_text = st.text_input(
            "Customer Request:",
            placeholder="e.g., Brake pads for '19 Honda Civic",
            help="Enter a parts query to test the RAG system"
        )
        
        location = st.selectbox(
            "Filter Location:",
            ["All", "Chicago North", "O'Hare Auto", "Logan Square Motors", 
             "Wrigley Dealership", "South Side Parts", "Loop Luxury Autos", "West Town Wheels"],
            help="Filter results by specific location"
        )
        
        urgency = st.selectbox(
            "Urgency Level:",
            ["normal", "urgent", "critical"],
            help="Set the urgency level for processing"
        )
        
        if st.button("🚀 Run RAG Magic", type="primary"):
            if query_text:
                payload = {
                    "text": query_text,
                    "location_filter": location if location != "All" else None,
                    "urgency": urgency
                }
                
                with st.spinner("Processing query..."):
                    try:
                        response = requests.post(QUERY_API_URL, json=payload, timeout=10)
                        if response.status_code == 200:
                            st.session_state.query_result = response.json()
                            st.success("Query processed successfully!")
                        else:
                            st.error(f"API Error: {response.status_code}")
                    except requests.exceptions.RequestException as e:
                        st.error(f"Connection error: {str(e)}")
            else:
                st.warning("Please enter a query first!")
    
    elif demo_mode == "Email Processing":
        st.subheader("Email Demo")
        
        if st.button("📧 Process Mock Emails", type="primary"):
            with st.spinner("Processing emails..."):
                try:
                    # Fetch and process mock emails
                    response = requests.post(f"{API_BASE_URL}/fetch_emails", timeout=10)
                    if response.status_code == 200:
                        st.session_state.email_results = response.json()
                        st.success("Emails processed!")
                    else:
                        st.error(f"Email API Error: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Connection error: {str(e)}")
    
    else:  # System Status
        st.subheader("System Health")
        if st.button("🔍 Check Status", type="primary"):
            with st.spinner("Checking system..."):
                try:
                    response = requests.get(f"{API_BASE_URL}/health", timeout=5)
                    if response.status_code == 200:
                        st.session_state.system_status = response.json()
                        st.success("System healthy!")
                    else:
                        st.error("System check failed")
                except requests.exceptions.RequestException as e:
                    st.error(f"Connection error: {str(e)}")

# Main content area
if demo_mode == "Parts Query" and 'query_result' in st.session_state:
    result = st.session_state.query_result
    
    # Color-coded result display
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("🎯 Result")
        
        # Display color-coded result
        color = result.get("color", "🟡")
        confidence = result.get("confidence", 0)
        
        if "🟢" in color:
            st.markdown(f"""
            <div class="success-box">
                <h3 style="color: #155724; margin: 0;">{color}</h3>
                <p style="margin: 0.5rem 0 0 0;">Auto-resolved with high confidence</p>
            </div>
            """, unsafe_allow_html=True)
        elif "🟡" in color:
            st.markdown(f"""
            <div class="warning-box">
                <h3 style="color: #856404; margin: 0;">{color}</h3>
                <p style="margin: 0.5rem 0 0 0;">Human review recommended</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="alert-box">
                <h3 style="color: #721c24; margin: 0;">{color}</h3>
                <p style="margin: 0.5rem 0 0 0;">Immediate escalation required</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Metrics
        st.metric("Confidence Score", f"{confidence:.2f}")
        st.metric("Processing Time", f"{result.get('processing_time_ms', 0)}ms")
        st.metric("Priority", result.get('priority', 'medium').title())
    
    with col2:
        st.subheader("🤖 AI Response")
        st.write(result.get("response", "No response generated"))
        
        # Payment status display
        if result.get("payment_status"):
            st.success("💳 Payment Processed Successfully!")
            col_pay1, col_pay2 = st.columns(2)
            with col_pay1:
                st.metric("Payment ID", result.get("payment_intent", {}).get("id", "N/A")[:20] + "...")
            with col_pay2:
                st.metric("Amount Charged", f"${result.get('amount_charged', 0):.2f}")
        
        st.subheader("📋 Next Steps")
        next_steps = result.get("next_steps", [])
        if next_steps:
            for i, step in enumerate(next_steps, 1):
                st.write(f"{i}. {step}")
        else:
            st.write("No specific next steps provided")
        
        # Suggestions
        suggestions = result.get("suggestions", [])
        if suggestions:
            st.subheader("💡 Suggestions")
            for suggestion in suggestions[:3]:  # Show top 3
                st.write(f"• {suggestion}")
    
    # Inventory matches
    inventory_matches = result.get("inventory_matches", [])
    if inventory_matches:
        st.subheader("📦 Inventory Matches")
        for i, match in enumerate(inventory_matches[:3], 1):
            with st.expander(f"Match {i} - Score: {match.get('relevance_score', 0):.2f}"):
                st.write(match.get("content", "No content"))
                if match.get("metadata"):
                    st.json(match["metadata"])

elif demo_mode == "Email Processing" and 'email_results' in st.session_state:
    email_results = st.session_state.email_results
    
    st.subheader("📧 Email Processing Results")
    
    # Email statistics
    if isinstance(email_results, list) and email_results:
        total_emails = len(email_results)
        auto_count = len([e for e in email_results if "🟢" in e.get("color", "")])
        review_count = len([e for e in email_results if "🟡" in e.get("color", "")])
        escalate_count = len([e for e in email_results if "🔴" in e.get("color", "")])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Emails", total_emails)
        with col2:
            st.metric("Auto-Processed", auto_count)
        with col3:
            st.metric("Need Review", review_count)
        with col4:
            st.metric("Escalated", escalate_count)
        
        # Individual email results
        for email in email_results:
            with st.expander(f"Email {email.get('email_id', 'N/A')}: {email.get('subject', 'No Subject')}"):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    color = email.get("color", "🟡")
                    if "🟢" in color:
                        st.success(color)
                    elif "🟡" in color:
                        st.warning(color)
                    else:
                        st.error(color)
                    
                    st.write(f"**From:** {email.get('from', 'Unknown')}")
                    st.write(f"**Confidence:** {email.get('confidence', 0):.2f}")
                
                with col2:
                    st.write("**Draft Reply:**")
                    st.write(email.get("draft_reply", "No reply generated"))
                    
                    # Payment information
                    if email.get("payment_status"):
                        st.success("💳 Payment Processed!")
                        st.write(f"**Order ID:** {email.get('order_id', 'N/A')}")
                        st.write(f"**Payment ID:** {email.get('payment_intent', {}).get('id', 'N/A')}")
                        st.write(f"**Amount:** ${email.get('amount_charged', 0):.2f}")
                    
                    if email.get("next_steps"):
                        st.write("**Next Steps:**")
                        for step in email.get("next_steps", []):
                            st.write(f"• {step}")

elif demo_mode == "System Status":
    st.subheader("🔍 System Health Check")
    
    # System status
    if 'system_status' in st.session_state:
        status = st.session_state.system_status
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Status", status.get("status", "Unknown"))
            st.metric("Database", status.get("database", "Unknown"))
            st.metric("Redis", status.get("redis", "Unknown"))
        
        with col2:
            st.metric("AI Services", status.get("ai_services", "Unknown"))
            st.metric("RAG System", status.get("rag_system", "Unknown"))
            st.metric("Last Check", datetime.now().strftime("%H:%M:%S"))
    
    # Analytics overview
    st.subheader("📊 Analytics Overview")
    try:
        metrics = generate_metrics()
        
        # Performance metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Avg Processing Time", f"{metrics['performance_metrics']['avg_processing_time_ms']}ms")
        with col2:
            st.metric("Avg Confidence", metrics['performance_metrics']['avg_confidence_score'])
        with col3:
            st.metric("Payment Rate", metrics['session_summary']['payment_success_rate'])
        
        # ROI metrics
        st.subheader("💰 ROI Projections")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Current Annual Cost", metrics['roi_projections']['current_annual_cost'])
        with col2:
            st.metric("Future Annual Cost", metrics['roi_projections']['future_annual_cost'])
        with col3:
            st.metric("Net Annual Savings", metrics['roi_projections']['net_annual_savings'])
        
        # Color distribution chart
        st.subheader("🎯 Automation Distribution")
        color_data = metrics['color_distribution']
        if sum(color_data.values()) > 0:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🟢 Auto", color_data['🟢'])
            with col2:
                st.metric("🟡 Review", color_data['🟡'])
            with col3:
                st.metric("🔴 Escalate", color_data['🔴'])
        
        # Export options
        st.subheader("📋 Export Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📄 Export JSON"):
                json_data = export_metrics("json")
                st.download_button(
                    label="Download JSON",
                    data=json_data,
                    file_name=f"parts_rag_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        with col2:
            if st.button("📊 Export CSV"):
                csv_data = export_metrics("csv")
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name=f"parts_rag_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        with col3:
            if st.button("📈 Export Analytics Report"):
                # Create comprehensive analytics report
                report_data = {
                    "Metric": [
                        "Total Queries",
                        "Green Automation Rate",
                        "Yellow Review Rate", 
                        "Red Escalation Rate",
                        "Payment Success Rate",
                        "Total Savings (Demo)",
                        "Average Savings per Query",
                        "Annual Savings Projected",
                        "Current Annual Cost",
                        "Future Annual Cost",
                        "Net Annual Savings",
                        "ROI Timeline (Months)",
                        "Average Processing Time (ms)",
                        "Average Confidence Score"
                    ],
                    "Value": [
                        metrics['session_summary']['total_queries'],
                        metrics['session_summary']['green_automation_rate'],
                        metrics['session_summary']['yellow_review_rate'],
                        metrics['session_summary']['red_escalation_rate'],
                        metrics['session_summary']['payment_success_rate'],
                        metrics['performance_metrics']['total_savings_demo'],
                        metrics['performance_metrics']['avg_savings_per_query'],
                        metrics['roi_projections']['annual_savings_projected'],
                        metrics['roi_projections']['current_annual_cost'],
                        metrics['roi_projections']['future_annual_cost'],
                        metrics['roi_projections']['net_annual_savings'],
                        metrics['roi_projections']['roi_timeline_months'],
                        metrics['performance_metrics']['avg_processing_time_ms'],
                        metrics['performance_metrics']['avg_confidence_score']
                    ]
                }
                
                df = pd.DataFrame(report_data)
                csv_buffer = StringIO()
                df.to_csv(csv_buffer, index=False)
                
                st.download_button(
                    label="Download Analytics Report",
                    data=csv_buffer.getvalue(),
                    file_name=f"parts_rag_analytics_report_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        
    except Exception as e:
        st.error(f"Analytics error: {str(e)}")

# Footer with demo info
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    <p>🚀 Lester's Parts RAG Demo - Enterprise AI for Dealerships</p>
    <p>API: <code>localhost:8000</code> | Mobile-optimized | Real-time processing</p>
</div>
""", unsafe_allow_html=True)

# Auto-refresh option
if st.checkbox("🔄 Auto-refresh (30s)", help="Automatically refresh the page every 30 seconds"):
    time.sleep(30)
    st.rerun()
