import React, { useState, useEffect } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';

interface NFTAttribute {
  traitType: string;
  value: string;
}

interface NFTMetadata {
  name: string;
  description: string;
  imageUrl: string;
  attributes: NFTAttribute[];
}

interface NFTPortfolioItem {
  nftId: string;
  nftType: string;
  metadata: NFTMetadata;
  mintTimestamp: number;
  isListed: boolean;
  listingPrice?: number;
  estimatedValue?: number;
}

interface MintNFTForm {
  nftType: 'certification' | 'investment_position' | 'reward';
  name: string;
  description: string;
  imageUrl: string;
  attributes: NFTAttribute[];
  quizScore?: number;
  rewardType?: string;
}

const NFTPortfolio: React.FC = () => {
  const { publicKey, connected } = useWallet();
  const [nfts, setNfts] = useState<NFTPortfolioItem[]>([]);
  const [showMintForm, setShowMintForm] = useState<boolean>(false);
  const [isMinting, setIsMinting] = useState<boolean>(false);
  
  const [mintForm, setMintForm] = useState<MintNFTForm>({
    nftType: 'certification',
    name: '',
    description: '',
    imageUrl: '',
    attributes: [],
    quizScore: 85
  });

  useEffect(() => {
    if (connected && publicKey) {
      fetchNFTPortfolio();
    }
  }, [connected, publicKey]);

  const fetchNFTPortfolio = async () => {
    try {
      const response = await fetch(`/api/nft/portfolio?wallet=${publicKey?.toString()}`);
      if (response.ok) {
        const data = await response.json();
        setNfts(data);
      }
    } catch (error) {
      console.error('Error fetching NFT portfolio:', error);
    }
  };

  const handleMintNFT = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!connected || !publicKey) return;

    setIsMinting(true);
    try {
      const response = await fetch('/api/nft/mint', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          wallet_address: publicKey.toString(),
          nft_type: mintForm.nftType,
          metadata: {
            name: mintForm.name,
            description: mintForm.description,
            image_url: mintForm.imageUrl,
            attributes: mintForm.attributes
          },
          quiz_score: mintForm.quizScore,
          reward_type: mintForm.rewardType
        })
      });

      if (response.ok) {
        const result = await response.json();
        alert(`NFT minted successfully! ID: ${result.nft_id}`);
        fetchNFTPortfolio();
        setShowMintForm(false);
        resetMintForm();
      }
    } catch (error) {
      console.error('Error minting NFT:', error);
      alert('Failed to mint NFT');
    } finally {
      setIsMinting(false);
    }
  };

  const resetMintForm = () => {
    setMintForm({
      nftType: 'certification',
      name: '',
      description: '',
      imageUrl: '',
      attributes: [],
      quizScore: 85
    });
  };

  const addAttribute = () => {
    setMintForm(prev => ({
      ...prev,
      attributes: [...prev.attributes, { traitType: '', value: '' }]
    }));
  };

  const updateAttribute = (index: number, field: 'traitType' | 'value', value: string) => {
    setMintForm(prev => ({
      ...prev,
      attributes: prev.attributes.map((attr, i) => 
        i === index ? { ...attr, [field]: value } : attr
      )
    }));
  };

  const removeAttribute = (index: number) => {
    setMintForm(prev => ({
      ...prev,
      attributes: prev.attributes.filter((_, i) => i !== index)
    }));
  };

  const listNFTForSale = async (nftId: string, price: number) => {
    try {
      const response = await fetch('/api/nft/list', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          nft_id: nftId,
          price: price * 1000000
        })
      });

      if (response.ok) {
        alert('NFT listed for sale successfully!');
        fetchNFTPortfolio();
      }
    } catch (error) {
      console.error('Error listing NFT:', error);
      alert('Failed to list NFT for sale');
    }
  };

  if (!connected) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">NFT Portfolio</h2>
        <p className="text-gray-600">Please connect your wallet to view your NFT portfolio.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">NFT Portfolio</h2>
          <button
            onClick={() => setShowMintForm(!showMintForm)}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
          >
            {showMintForm ? 'Cancel' : 'Mint New NFT'}
          </button>
        </div>

        {showMintForm && (
          <form onSubmit={handleMintNFT} className="mb-6 p-4 border border-gray-200 rounded-lg">
            <h3 className="text-lg font-medium mb-4">Mint New NFT</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  NFT Type
                </label>
                <select
                  value={mintForm.nftType}
                  onChange={(e) => setMintForm(prev => ({ ...prev, nftType: e.target.value as 'certification' | 'investment_position' | 'reward' }))}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                >
                  <option value="certification">Certification NFT</option>
                  <option value="investment_position">Investment Position NFT</option>
                  <option value="reward">Reward NFT</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Name
                </label>
                <input
                  type="text"
                  value={mintForm.name}
                  onChange={(e) => setMintForm(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                  placeholder="NFT Name"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Description
                </label>
                <textarea
                  value={mintForm.description}
                  onChange={(e) => setMintForm(prev => ({ ...prev, description: e.target.value }))}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                  rows={3}
                  placeholder="NFT Description"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Image URL
                </label>
                <input
                  type="url"
                  value={mintForm.imageUrl}
                  onChange={(e) => setMintForm(prev => ({ ...prev, imageUrl: e.target.value }))}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                  placeholder="https://example.com/image.png"
                  required
                />
              </div>

              {mintForm.nftType === 'certification' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Quiz Score (%)
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={mintForm.quizScore || ''}
                    onChange={(e) => setMintForm(prev => ({ ...prev, quizScore: parseInt(e.target.value) }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                    placeholder="85"
                    required
                  />
                </div>
              )}

              {mintForm.nftType === 'reward' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Reward Type
                  </label>
                  <select
                    value={mintForm.rewardType || ''}
                    onChange={(e) => setMintForm(prev => ({ ...prev, rewardType: e.target.value }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                    required
                  >
                    <option value="">Select reward type</option>
                    <option value="roi_milestone">ROI Milestone</option>
                    <option value="referral_bonus">Referral Bonus</option>
                    <option value="compliance_achievement">Compliance Achievement</option>
                    <option value="trading_volume">Trading Volume</option>
                  </select>
                </div>
              )}

              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Attributes
                  </label>
                  <button
                    type="button"
                    onClick={addAttribute}
                    className="text-blue-600 hover:text-blue-800 text-sm"
                  >
                    + Add Attribute
                  </button>
                </div>
                
                {mintForm.attributes.map((attribute, index) => (
                  <div key={index} className="flex space-x-2 mb-2">
                    <input
                      type="text"
                      value={attribute.traitType}
                      onChange={(e) => updateAttribute(index, 'traitType', e.target.value)}
                      className="flex-1 border border-gray-300 rounded px-2 py-1 text-sm"
                      placeholder="Trait Type"
                    />
                    <input
                      type="text"
                      value={attribute.value}
                      onChange={(e) => updateAttribute(index, 'value', e.target.value)}
                      className="flex-1 border border-gray-300 rounded px-2 py-1 text-sm"
                      placeholder="Value"
                    />
                    <button
                      type="button"
                      onClick={() => removeAttribute(index)}
                      className="text-red-600 hover:text-red-800 text-sm px-2"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>

              <button
                type="submit"
                disabled={isMinting}
                className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                {isMinting ? 'Minting...' : 'Mint NFT'}
              </button>
            </div>
          </form>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {nfts.length === 0 ? (
            <div className="col-span-full text-center py-8">
              <p className="text-gray-600">No NFTs found. Mint your first NFT to get started!</p>
            </div>
          ) : (
            nfts.map(nft => (
              <div key={nft.nftId} className="border border-gray-200 rounded-lg p-4">
                <div className="aspect-square bg-gray-100 rounded-lg mb-3 overflow-hidden">
                  <img
                    src={nft.metadata.imageUrl}
                    alt={nft.metadata.name}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPk5GVCBJbWFnZTwvdGV4dD48L3N2Zz4=';
                    }}
                  />
                </div>
                
                <div className="space-y-2">
                  <div className="flex justify-between items-start">
                    <h4 className="font-medium text-lg">{nft.metadata.name}</h4>
                    <span className={`px-2 py-1 text-xs rounded ${
                      nft.nftType === 'certification' ? 'bg-blue-100 text-blue-800' :
                      nft.nftType === 'investment_position' ? 'bg-green-100 text-green-800' :
                      'bg-purple-100 text-purple-800'
                    }`}>
                      {nft.nftType.replace('_', ' ').toUpperCase()}
                    </span>
                  </div>
                  
                  <p className="text-sm text-gray-600 line-clamp-2">{nft.metadata.description}</p>
                  
                  {nft.metadata.attributes.length > 0 && (
                    <div className="space-y-1">
                      {nft.metadata.attributes.slice(0, 3).map((attr, index) => (
                        <div key={index} className="flex justify-between text-xs">
                          <span className="text-gray-500">{attr.traitType}:</span>
                          <span className="font-medium">{attr.value}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  <div className="flex justify-between items-center pt-2 border-t border-gray-100">
                    <div className="text-sm text-gray-600">
                      Minted: {new Date(nft.mintTimestamp * 1000).toLocaleDateString()}
                    </div>
                    {nft.estimatedValue && (
                      <div className="text-sm font-medium">
                        ~{(nft.estimatedValue / 1000000).toFixed(3)} SOL
                      </div>
                    )}
                  </div>
                  
                  {!nft.isListed && (
                    <button
                      onClick={() => {
                        const price = prompt('Enter listing price in SOL:');
                        if (price) {
                          listNFTForSale(nft.nftId, parseFloat(price));
                        }
                      }}
                      className="w-full bg-blue-600 text-white py-1 px-3 rounded text-sm hover:bg-blue-700"
                    >
                      List for Sale
                    </button>
                  )}
                  
                  {nft.isListed && nft.listingPrice && (
                    <div className="text-center">
                      <div className="text-sm text-green-600 font-medium">
                        Listed for {(nft.listingPrice / 1000000).toFixed(3)} SOL
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default NFTPortfolio;
