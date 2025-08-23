import React, { useState } from 'react';

const AccessibilitySample: React.FC = () => {
    const [isVisible, setIsVisible] = useState(false);

    const handleClick = () => {
        setIsVisible(!isVisible);
    };

    return (
        <div>
            {/* This should trigger jsx-a11y/img-redundant-alt */}
            <img src="/logo.png" alt="Logo image" />
            
            {/* This should trigger jsx-a11y/anchor-is-valid */}
            <a href="#" onClick={handleClick}>Click me</a>
            
            {/* This should trigger jsx-a11y/click-events-have-key-events */}
            <div onClick={handleClick}>
                Clickable div without keyboard support
            </div>
            
            {/* This should trigger jsx-a11y/label-has-associated-control */}
            <label>Email:</label>
            <input type="email" />
            
            {/* This should trigger jsx-a11y/html-has-lang */}
            <iframe src="/content.html" title="Content frame" />
            
            {/* This should trigger jsx-a11y/tabindex-no-positive */}
            <button tabIndex={1}>Submit</button>
            
            {isVisible && (
                <div>
                    {/* This should trigger jsx-a11y/heading-has-content */}
                    <h1></h1>
                    <p>Content is now visible</p>
                </div>
            )}
        </div>
    );
};

export default AccessibilitySample;
